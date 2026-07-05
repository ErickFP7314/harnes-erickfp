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
estos errores: nunca se silencia un fallo real distinto ni el ultimo intento
transitorio agotado.

Retry configurable (Lote 2 harness-v0-2, tarea 2.2, design.md Decision 10):
`max_attempts`/`backoff_seconds` son atributos del constructor -- ya no
constantes de modulo -- para que `cli`/config puedan ajustarlos sin tocar
este archivo. El default (`max_attempts=2, backoff_seconds=2.0`) preserva
bit-a-bit el comportamiento del ciclo 1.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

import litellm

from erickfp.api.types import Block, Message, Response, ToolDef, Usage
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

# Defaults de retry (Decision 10): preservan bit-a-bit el comportamiento del
# ciclo 1 (1 llamada real + a lo sumo 1 reintento) cuando el constructor no
# recibe overrides. Cualquier otro error, o el ultimo intento transitorio
# agotado, se propaga como `ProviderError` -- nunca se silencia un fallo real.
_DEFAULT_MAX_ATTEMPTS = 2
_DEFAULT_BACKOFF_SECONDS = 2.0
_TRANSIENT_ERROR_MARKERS = ("500", "INTERNAL")

# Normalizacion de `stop_reason` (hallazgo del smoke E2E real, Lote 9 harness-
# v0-2, tasks.md 9.2, design.md Decision 2): litellm reenvia `finish_reason`
# en la convencion nativa OpenAI-style ("stop"/"tool_calls"/"length"/...),
# pero el resto del dominio (agent/agent.py::Agent.run_turn, TODOS los
# Provider fakes de tests/agent/) asume la convencion canonica Anthropic-
# style ya usada en `Block.type` ("tool_use"/"end_turn"). Sin esta tabla, el
# string crudo de litellm cruzaba intacto hacia `Response.stop_reason` --
# contra un fake esto nunca fallaba (los fakes ya emiten el string
# canonico), pero contra Gemini/Gemma real el mismatch hacia que
# `Agent.run_turn` (`stop_reason != "tool_use"`) SIEMPRE devolviera el turno
# de inmediato, saltandose el permission gate por completo aunque el modelo
# SI pidiera una tool real. Cualquier `finish_reason` no listado (valor
# nuevo de litellm, o ausente) cae a "end_turn" -- el mismo default seguro
# que ya tenia esta funcion antes de esta tabla.
_STOP_REASON_MAP: dict[str, str] = {
    "tool_calls": "tool_use",
    "stop": "end_turn",
}


class LiteLLMGeminiProvider:
    """Adapter `Provider` (Decision 5) que traduce hacia/desde LiteLLM + Gemini."""

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        sleep_fn: Callable[[float], None] = time.sleep,
        max_attempts: int = _DEFAULT_MAX_ATTEMPTS,
        backoff_seconds: float = _DEFAULT_BACKOFF_SECONDS,
    ) -> None:
        self._model_name = model_name
        self._sleep_fn = sleep_fn
        self._max_attempts = max_attempts
        self._backoff_seconds = backoff_seconds

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
        """Llama a `litellm.completion` con hasta `self._max_attempts`
        intentos: reintenta, tras `self._backoff_seconds` de espera, solo si
        el error es transitorio (`500`/`INTERNAL` en el mensaje, spike 2.2).
        Cualquier otro error -- o el ultimo intento transitorio agotado --
        se traduce a `ProviderError` (dominio) en vez de relanzar la
        excepcion nativa del SDK (Decision 10, tarea 2.3)."""
        for attempt in range(self._max_attempts):
            try:
                return litellm.completion(**kwargs)
            except Exception as exc:
                is_transient = any(marker in str(exc) for marker in _TRANSIENT_ERROR_MARKERS)
                is_last_attempt = attempt == self._max_attempts - 1
                if not is_transient or is_last_attempt:
                    # Fallo definitivo: se traduce a ProviderError (dominio)
                    # para que las capas superiores fallen limpio sin conocer
                    # los tipos de excepcion de litellm (hotfix 2026-07-04).
                    raise ProviderError(str(exc)) from exc
                self._sleep_fn(self._backoff_seconds)
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

        raw_finish_reason = getattr(choice, "finish_reason", None) or "end_turn"
        stop_reason = _STOP_REASON_MAP.get(raw_finish_reason, "end_turn")
        return Response(content=blocks, stop_reason=stop_reason, usage=self._to_usage(raw))

    def _to_usage(self, raw: Any) -> Usage | None:
        """Traduce `raw.usage` (forma nativa de litellm) al tipo de dominio
        `Usage` (Lote 3 harness-v0-2, tarea 3.13, design.md Decision 6).
        `raw.usage` puede no existir (algunos mocks de prueba no lo modelan)
        -- en ese caso retorna `None` en vez de lanzar."""
        raw_usage = getattr(raw, "usage", None)
        if raw_usage is None:
            return None
        return Usage(
            prompt=getattr(raw_usage, "prompt_tokens", 0) or 0,
            completion=getattr(raw_usage, "completion_tokens", 0) or 0,
            total=getattr(raw_usage, "total_tokens", 0) or 0,
        )
