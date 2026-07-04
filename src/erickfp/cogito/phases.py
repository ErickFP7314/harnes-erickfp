"""cogito/phases.py -- ejecucion de una fase individual del Ciclo Cogito
(Decision 4 del design; spec ciclo-cogito).

Cada fase envia un turno al Provider con el rol correspondiente (Planner en
`duda`/`divide`, Coder en `ordena`, Reviewer en `enumera`, Requirement
'Modos y roles por fase') mas el texto de entrada: el objetivo del usuario
para `duda`, o el artefacto de la fase previa para las demas.

Solo `duda` puede negarse a producir un artefacto (Requirement 'duda exige
claridad antes de avanzar'): un protocolo de marcadores explicitos
(`AMBIGUOUS_MARKER`/`ACCEPTED_MARKER`) inyectado en las instrucciones de la
fase le permite al modelo declarar sin ambiguedad si el objetivo es claro.
Sin un marcador reconocido, se trata como ambiguo (fail-safe): nunca se
genera un artefacto que el modelo no marco explicitamente como aceptado.

Este modulo depende de `erickfp.agent.loop.run_turn` -- dependencia real no
listada en el arbol de paquetes de Decision 1 del design (que solo enumera
`cogito -> api,provider,tools,hooks,memory`), igual que la omision de
`erickfp.agent` ya documentada en la Fase 8/Lote 4. Es necesaria porque el
"Secuencia" del design describe explicitamente "agent loop (send preserva
provider_metadata)" como parte de la ejecucion de cada fase, y el contrato
`import-linter` ya ubica `erickfp.cogito` por encima de `erickfp.agent` en
las capas (`pyproject.toml`), por lo que esta dependencia esta permitida sin
tocar el contrato.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from erickfp.agent.loop import run_turn
from erickfp.api.types import Block, Message
from erickfp.provider.base import Provider
from erickfp.tools.registry import ToolRegistry

ROLE_BY_PHASE = {
    "duda": "planner",
    "divide": "planner",
    "ordena": "coder",
    "enumera": "reviewer",
}
PREVIOUS_PHASE: dict[str, str | None] = {
    "duda": None,
    "divide": "duda",
    "ordena": "divide",
    "enumera": "ordena",
}
PHASE_SEQUENCE = ["duda", "divide", "ordena", "enumera"]

ACCEPTED_MARKER = "ACEPTADO:"
AMBIGUOUS_MARKER = "AMBIGUO:"

_DUDA_INSTRUCTIONS = (
    "Estas en la fase 'duda' del Ciclo Cogito: somete el objetivo a duda "
    "metodica. Si detectas requisitos contradictorios o ambiguedad real, "
    "responde EXCLUSIVAMENTE con una linea que empiece por "
    f"'{AMBIGUOUS_MARKER}' seguida de las preguntas de clarificacion -- NO "
    "generes artefacto. Si el objetivo es claro y distinto, responde "
    f"EXCLUSIVAMENTE con una linea que empiece por '{ACCEPTED_MARKER}' "
    "seguida del artefacto duda.md completo."
)

_ARTIFACT_INSTRUCTIONS = {
    "divide": "Genera el artefacto divide.md: descompon el objetivo en sus partes minimas.",
    "ordena": "Genera el artefacto ordena.md: sintetiza segun el plan de divide.md.",
    "enumera": "Genera el artefacto enumera.md: revisa y enumera los resultados de ordena.md.",
}


@dataclass
class PhaseResult:
    status: Literal["artifact", "clarification"]
    content: str


def run_phase(
    provider: Provider,
    tools: ToolRegistry,
    phase: str,
    role_prompt: str,
    input_text: str,
) -> PhaseResult:
    """Ejecuta un turno completo (via `agent.loop.run_turn`) para `phase` y
    clasifica la respuesta en artefacto aceptado o clarificacion pendiente."""
    task_instructions = _DUDA_INSTRUCTIONS if phase == "duda" else _ARTIFACT_INSTRUCTIONS[phase]
    prompt = "\n\n".join(part for part in (role_prompt, task_instructions, input_text) if part)

    messages = [Message(role="user", content=[Block(type="text", text=prompt)])]
    result_messages = run_turn(provider, tools, messages, tools.definitions())
    text = _extract_text(result_messages[-1])

    if phase == "duda":
        return _classify_duda_response(text)
    return PhaseResult(status="artifact", content=text)


def _classify_duda_response(text: str) -> PhaseResult:
    stripped = text.strip()
    if stripped.startswith(AMBIGUOUS_MARKER):
        clarification = stripped[len(AMBIGUOUS_MARKER) :].strip()
        return PhaseResult(status="clarification", content=clarification)
    if stripped.startswith(ACCEPTED_MARKER):
        accepted_content = stripped[len(ACCEPTED_MARKER) :].strip()
        return PhaseResult(status="artifact", content=accepted_content)
    return PhaseResult(status="clarification", content=stripped)


def _extract_text(message: Message) -> str:
    return "\n".join(block.text for block in message.content if block.type == "text" and block.text)
