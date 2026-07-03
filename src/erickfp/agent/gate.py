"""agent/gate.py -- permission gate (Decision 3 del design; spec agent-loop,
Requirement 'Permission gate sin fuga').

Toda tool call, sin excepcion de tipo de tool o fase, pasa por este gate
antes de `tool.execute()`. Consume `input()` a traves de `read_line()`
(patron validado en el spike 2.3, docs/spikes/repl-input.md): un unico punto
de entrada a stdin en todo el proceso -- ningun otro modulo debe leer
`sys.stdin` por una via alterna. El gate NUNCA lanza una excepcion: el
default ante respuesta vacia o ambigua es SIEMPRE deny.
"""

from __future__ import annotations

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


def run_tool_with_gate(tool: Tool, tool_use: Block) -> Block:
    """Ejecuta `tool` SOLO si el humano aprueba explicitamente.

    Retorna SIEMPRE un `Block` tipo `tool_result` -- jamas lanza una
    excepcion. Si el humano niega, `is_error=True` con una razon legible;
    la tool real nunca se invoca en ese caso (contrato de Decision 3: deny
    -> tool_result is_error=true, nunca excepcion).
    """
    if confirm(tool.definition().name, tool_use.tool_input):
        result_text, is_error = tool.execute(tool_use.tool_input)
    else:
        result_text, is_error = _DENIAL_REASON, True

    return Block(
        type="tool_result",
        tool_use_id=tool_use.tool_use_id,
        tool_result=result_text,
        is_error=is_error,
    )
