"""agent/policy.py -- PermissionPolicy pluggable (Decision 2 del design;
spec permission-policy, Requirement 'Interfaz PermissionPolicy con default
AlwaysAsk').

`PermissionPolicy` es un `typing.Protocol`: cualquier objeto con un metodo
`decide(tool_name, tool_input) -> Literal["allow", "deny", "ask"]` lo
satisface, sin heredar de nada (mismo patron estructural que `Provider`/
`Tool`/`Hook`, Decision 5). El gate (`agent/gate.py::run_tool_with_gate`)
consulta esta decision ANTES de decidir si pregunta al humano:

- "allow" -> ejecuta la tool sin preguntar.
- "deny"  -> `tool_result is_error=true`, la tool real nunca se invoca.
- "ask"   -> el gate pregunta y/n via `confirm()`, igual que el ciclo 1.

El core_guard (`PreToolUse` en `hooks/core_guard.py`) se evalua en
`agent/loop.py` ANTES de siquiera llegar a este modulo -- ninguna
implementacion de aqui puede aprobar una escritura en `core/*` (Requirement
'core_guard prevalece sobre cualquier policy'): ese veto ocurre aguas arriba
del gate, sin excepcion.
"""

from __future__ import annotations

from typing import Literal, Protocol

Decision = Literal["allow", "deny", "ask"]


class PermissionPolicy(Protocol):
    """Estructura minima que toda policy debe satisfacer."""

    def decide(self, tool_name: str, tool_input: str) -> Decision: ...


class AlwaysAsk:
    """Default (Scenario 'AlwaysAsk equivalente al gate del ciclo 1'):
    siempre responde "ask" -- el gate pregunta y/n en cada tool call, igual
    que el comportamiento del ciclo 1 sin policy configurada."""

    def decide(self, tool_name: str, tool_input: str) -> Decision:
        return "ask"


class AllowList:
    """Aprueba sin preguntar las tools cuyo nombre esta en la lista
    preconfigurada (Scenario 'AllowList aprueba sin preguntar'); cualquier
    otra tool sigue preguntando (nunca deniega por si sola: solo reduce
    friccion, no amplia el universo de tools disponibles)."""

    def __init__(self, allowed_tool_names: set[str] | frozenset[str]) -> None:
        self._allowed = frozenset(allowed_tool_names)

    def decide(self, tool_name: str, tool_input: str) -> Decision:
        return "allow" if tool_name in self._allowed else "ask"


class AskOnce:
    """Pregunta una sola vez por tool durante la sesion (Scenario 'AskOnce
    pregunta una sola vez por sesion'): la aprobacion se memoriza EN el
    objeto (estado de sesion, nunca persiste a disco). La negacion (incluida
    una respuesta ambigua) NUNCA se cachea -- la proxima tool call de esa
    misma tool vuelve a preguntar (Scenario 'Respuesta ambigua bajo
    AskOnce')."""

    def __init__(self) -> None:
        self._approved_tool_names: set[str] = set()

    def decide(self, tool_name: str, tool_input: str) -> Decision:
        if tool_name in self._approved_tool_names:
            return "allow"
        return "ask"

    def record_decision(self, tool_name: str, approved: bool) -> None:
        """Invocado por el gate DESPUES de resolver un "ask" real (nunca por
        `decide()` -- que es de solo lectura). Solo la aprobacion se
        recuerda; la negacion es un no-op deliberado."""
        if approved:
            self._approved_tool_names.add(tool_name)
