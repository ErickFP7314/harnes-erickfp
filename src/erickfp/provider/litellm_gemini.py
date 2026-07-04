"""provider/litellm_gemini.py -- adapter LiteLLM hacia Gemini (Decision 2 del design).

UNICO modulo del paquete que puede importar `litellm` (regla de frontera de
Decision 1/2, verificada por tests/test_no_native_sdk_leak.py). Traduce la
respuesta cruda de LiteLLM a los tipos propios (`Message`/`Block`/`Response`)
y preserva la thought signature de Gemini 3 entre turnos.

Mecanismo de thought signature (spike 2.1, docs/spikes/thought-signature.md,
analisis estatico de litellm==1.83.7 -- validacion empirica pendiente de una
GEMINI_API_KEY nueva, la actual esta revocada por Google):
- Con tool_use: litellm embebe la firma dentro del campo `id` del tool_call
  devuelto (separador `__thought__`). Basta con reenviar ese mismo id intacto
  en el turno siguiente para que litellm reconstruya `thoughtSignature` en el
  payload saliente a Gemini.
- Sin tool_use (solo texto): la firma viaja en
  `message.provider_specific_fields["thought_signatures"]`.
El agent loop trata `Block.provider_metadata` como bytes opacos; solo este
adapter lee/escribe su contenido.

Retry con backoff ante `500`/`INTERNAL` transitorios (Fase 11, tarea 11.5;
hallazgo del spike 2.2, docs/spikes/free-tier-limits.md: con Gemma 4, 1 de 11
llamadas reales consecutivas fallo con un 500 esporadico del servidor, sin
relacion con la cuota). Extiende el patron ya usado en
`scripts/spike_thought_signature.py::_call_with_backoff` (alli para 429) a
estos errores: UN solo reintento acotado, nunca se silencia un fallo real
distinto ni un segundo 500 consecutivo.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

import litellm

from erickfp.api.types import Block, Message, Response, ToolDef
from erickfp.provider.base import ProviderError

# ADR-001 (2026-07-03): default elegido por el usuario con evidencia del spike
# 2.1 (docs/spikes/thought-signature.md) — Gemma 4 acepta `tools`, devuelve
# tool calls parseables y el round-trip de thought signatures funciona.
# Trade-off aceptado: mas lento que gemini-3.5-flash (3.8s/8.8s vs 2.4s/2.0s)
# a cambio de modelo abierto y cuota free tier mas generosa. Siempre
# configurable via set_model()/constructor; esto fija solo el default.
DEFAULT_MODEL = "gemini/gemma-4-26b-a4b-it"

# Separador documentado en litellm/litellm_core_utils/prompt_templates/factory.py:64.
THOUGHT_SIGNATURE_SEPARATOR = "__thought__"

# Reintento ACOTADO: 1 llamada real + a lo sumo 1 reintento (2 intentos en
# total) ante 500/INTERNAL transitorios (spike 2.2). Cualquier otro error, o
# un segundo 500 consecutivo, se propaga tal cual -- nunca se silencia un
# fallo real.
_MAX_ATTEMPTS = 2
_BACKOFF_SECONDS = 2.0
_TRANSIENT_ERROR_MARKERS = ("500", "INTERNAL")


class LiteLLMGeminiProvider:
    """Adapter `Provider` (Decision 5) que traduce hacia/desde LiteLLM + Gemini."""

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        sleep_fn: Callable[[float], None] = time.sleep,
    ) -> None:
        self._model_name = model_name
        self._sleep_fn = sleep_fn

    def model(self) -> str:
        return self._model_name

    def set_model(self, name: str) -> None:
        self._model_name = name

    def send(self, messages: list[Message], tools: list[ToolDef]) -> Response:
        payload_messages: list[dict[str, Any]] = []
        for message in messages:
            payload_messages.extend(self._to_litellm_messages(message))

        payload_tools = [self._to_litellm_tool(tool) for tool in tools] if tools else None

        raw = self._call_with_backoff(
            model=self._model_name,
            messages=payload_messages,
            tools=payload_tools,
        )
        return self._to_response(raw)

    def _call_with_backoff(self, **kwargs: Any) -> Any:
        """Llama a `litellm.completion` con hasta `_MAX_ATTEMPTS` intentos:
        reintenta UNA vez, tras `_BACKOFF_SECONDS` de espera, solo si el error
        es transitorio (`500`/`INTERNAL` en el mensaje, spike 2.2). Cualquier
        otro error -- o un segundo error transitorio -- se relanza tal cual."""
        for attempt in range(_MAX_ATTEMPTS):
            try:
                return litellm.completion(**kwargs)
            except Exception as exc:
                is_transient = any(marker in str(exc) for marker in _TRANSIENT_ERROR_MARKERS)
                is_last_attempt = attempt == _MAX_ATTEMPTS - 1
                if not is_transient or is_last_attempt:
                    # Fallo definitivo: se traduce a ProviderError (dominio)
                    # para que las capas superiores fallen limpio sin conocer
                    # los tipos de excepcion de litellm (hotfix 2026-07-04).
                    raise ProviderError(str(exc)) from exc
                self._sleep_fn(_BACKOFF_SECONDS)
        raise AssertionError("inalcanzable: el loop siempre retorna o relanza")  # pragma: no cover

    # -- traduccion hacia LiteLLM --------------------------------------------

    def _to_litellm_messages(self, message: Message) -> list[dict[str, Any]]:
        if message.role == "assistant":
            return [self._assistant_message(message)]
        return self._user_message(message)

    def _assistant_message(self, message: Message) -> dict[str, Any]:
        text_parts = [
            block.text for block in message.content if block.type == "text" and block.text
        ]
        tool_use_blocks = [block for block in message.content if block.type == "tool_use"]

        entry: dict[str, Any] = {
            "role": "assistant",
            "content": "\n".join(text_parts) if text_parts else None,
        }
        if tool_use_blocks:
            entry["tool_calls"] = [
                {
                    # Reenviar el id crudo (con __thought__ si litellm lo
                    # embebio) es lo que permite el round-trip de la firma.
                    "id": block.provider_metadata.get("raw_tool_call_id", block.tool_use_id),
                    "type": "function",
                    "function": {"name": block.tool_name, "arguments": block.tool_input},
                }
                for block in tool_use_blocks
            ]

        thought_signatures = next(
            (
                block.provider_metadata["thought_signatures"]
                for block in message.content
                if block.provider_metadata.get("thought_signatures")
            ),
            None,
        )
        if thought_signatures:
            entry["provider_specific_fields"] = {"thought_signatures": thought_signatures}

        return entry

    def _user_message(self, message: Message) -> list[dict[str, Any]]:
        tool_results = [block for block in message.content if block.type == "tool_result"]
        if tool_results:
            return [
                {
                    "role": "tool",
                    "tool_call_id": block.tool_use_id,
                    "content": block.tool_result,
                }
                for block in tool_results
            ]

        text_parts = [block.text for block in message.content if block.type == "text"]
        return [{"role": "user", "content": "\n".join(text_parts)}]

    def _to_litellm_tool(self, tool: ToolDef) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.input_schema,
            },
        }

    # -- traduccion desde LiteLLM ---------------------------------------------

    def _to_response(self, raw: Any) -> Response:
        choice = raw.choices[0]
        message = choice.message
        blocks: list[Block] = []

        text = getattr(message, "content", None)
        if text:
            blocks.append(Block(type="text", text=text))

        tool_calls = getattr(message, "tool_calls", None) or []
        for call in tool_calls:
            call_id = call.id
            blocks.append(
                Block(
                    type="tool_use",
                    tool_use_id=call_id,
                    tool_name=call.function.name,
                    tool_input=call.function.arguments,
                    provider_metadata={"raw_tool_call_id": call_id},
                )
            )

        provider_specific = getattr(message, "provider_specific_fields", None) or {}
        thought_signatures = (
            provider_specific.get("thought_signatures")
            if isinstance(provider_specific, dict)
            else None
        )
        if thought_signatures and not tool_calls:
            if blocks:
                blocks[0].provider_metadata["thought_signatures"] = thought_signatures
            else:
                blocks.append(
                    Block(type="text", provider_metadata={"thought_signatures": thought_signatures})
                )

        stop_reason = getattr(choice, "finish_reason", None) or "end_turn"
        return Response(content=blocks, stop_reason=stop_reason)
