"""agent/gate.py -- permission gate (Decision 3 del design; spec agent-loop,
Requirement 'Permission gate sin fuga'; extendido Lote 4 harness-v0-2 --
Decision 2, spec permission-policy).

Toda tool call, sin excepcion de tipo de tool o fase, pasa por este gate
antes de `tool.execute()`. Consume `input()` a traves de `read_line()`
(patron validado en el spike 2.3, docs/spikes/repl-input.md): un unico punto
de entrada a stdin en todo el proceso -- ningun otro modulo debe leer
`sys.stdin` por una via alterna. El gate NUNCA lanza una excepcion: el
default ante respuesta vacia o ambigua es SIEMPRE deny.

`policy` (Lote 4, opcional, default `None`) es la `PermissionPolicy`
consultada ANTES de decidir si se pregunta al humano: `None` equivale a
`AlwaysAsk()` -- preserva bit-a-bit el comportamiento del ciclo 1 para todo
llamador que no inyecte una policy explicita (retrocompatibilidad total).
"""

from __future__ import annotations

from erickfp.agent.policy import AlwaysAsk, PermissionPolicy
from erickfp.api.types import Block
from erickfp.tools.base import Tool

_APPROVE = "y"
_DENIAL_REASON = "el humano nego la ejecucion de la tool (o no respondio 'y' explicito)"


def read_line(prompt: str) -> str:
    """Unico consumer de stdin del proceso (spike 2.3). Tanto el gate como
    cualquier prompt de confirmacion de fase (Fase 7/10) DEBEN llamar a esta
    misma funcion -- nunca leer `sys.stdin` por una via alterna.
    """
    return input(prompt)


def confirm(tool_name: str, tool_input: str) -> bool:
    """Pregunta y/n al humano. Default (vacio o cualquier cosa != 'y' exacto,
    tras `strip()`) es deny -- nunca se interpreta de forma laxa (ni
    mayusculas, ni 'yes') para no debilitar el gate (Scenario 'Respuesta
    vacia o no reconocida').
    """
    answer = read_line(f"Ejecutar {tool_name}({tool_input})? [y/N] ")
    return answer.strip() == _APPROVE


def run_tool_with_gate(
    tool: Tool, tool_use: Block, policy: PermissionPolicy | None = None
) -> Block:
    """Ejecuta `tool` SOLO si la policy activa lo permite (Lote 4, Decision
    2 del design): consulta `policy.decide(tool_name, tool_input)` -- ANTES
    de decidir si pregunta al humano -- con `policy=None` (default)
    equivalente a `AlwaysAsk()`, preservando bit-a-bit el comportamiento del
    ciclo 1 (Scenario 'AlwaysAsk equivalente al gate del ciclo 1').

    - "allow" -> ejecuta la tool sin preguntar (`AllowList`).
    - "deny"  -> `tool_result is_error=true`, la tool real nunca se invoca.
    - "ask"   -> pregunta y/n via `confirm()`; si la policy expone
      `record_decision` (duck-typing, p.ej. `AskOnce`) se le informa el
      resultado para que memorice SOLO la aprobacion (nunca la negacion,
      Scenario 'Respuesta ambigua bajo AskOnce').

    Retorna SIEMPRE un `Block` tipo `tool_result` -- jamas lanza una
    excepcion (contrato de Decision 3: deny -> tool_result is_error=true,
    nunca excepcion).
    """
    active_policy: PermissionPolicy = policy if policy is not None else AlwaysAsk()
    tool_name = tool.definition().name
    decision = active_policy.decide(tool_name, tool_use.tool_input)

    if decision == "deny":
        result_text, is_error = _DENIAL_REASON, True
    elif decision == "allow":
        result_text, is_error = tool.execute(tool_use.tool_input)
    else:
        approved = confirm(tool_name, tool_use.tool_input)
        record_decision = getattr(active_policy, "record_decision", None)
        if record_decision is not None:
            record_decision(tool_name, approved)
        if approved:
            result_text, is_error = tool.execute(tool_use.tool_input)
        else:
            result_text, is_error = _DENIAL_REASON, True

    return Block(
        type="tool_result",
        tool_use_id=tool_use.tool_use_id,
        tool_result=result_text,
        is_error=is_error,
    )
