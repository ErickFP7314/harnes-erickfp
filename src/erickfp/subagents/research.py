"""subagents/research.py -- subagente `Research` read-only (Lote 7
harness-v0-2, tareas 7.3-7.4, design.md Decision 7 / spec subagents,
Requirement 'Agent reutilizable y subagente Research read-only').

Construye un `Agent` (capa `agent`, Lote 7) con un `ToolRegistry` SUBSET
que contiene UNICAMENTE tools de lectura (`read_file`) -- `write_file` y
`bash` NUNCA se registran en ese subset. Una invocacion a cualquiera de
esas dos tools dentro del subagente falla exactamente igual que cualquier
tool ausente del registry ("tool desconocida en el registry", `agent.
agent.Agent.run_turn`): no existe ninguna comprobacion especial de
permisos para "prohibir escritura" -- la restriccion es, literalmente, que
la tool no esta ahi (Scenario 'Research no puede escribir').

La aprobacion humana de la tool call `delegate_research` (otorgada en el
agente principal, fuera de este modulo) cubre TODAS las tool calls
internas: se inyecta `AllowList` con el universo COMPLETO de tools del
subset (auto-allow), de modo que ninguna de ellas vuelve a preguntar y/n
(Requirement 'Aprobacion del delegate cubre las tool calls del
subagente'). El `core_guard` sigue activo si se inyecta un `hook_manager`
real: `core_guard` nunca depende de la policy activa (Requirement
'core_guard prevalece sobre cualquier policy', ya validado en el Lote 4) --
proteger `core/*` no es un concern de este modulo, es una garantia
transversal de `Agent`/`PreToolUse`.

`_MAX_TURNS` (mismo valor que `MaxTurns=10` del subagente Research de la
guia byo-coding-agent, capitulo 11) acota la investigacion: una tarea
delegada nunca itera indefinidamente sin devolver el control al agente
principal.
"""

from __future__ import annotations

from erickfp.agent.agent import Agent
from erickfp.agent.policy import AllowList
from erickfp.api.types import Block, Message
from erickfp.hooks.manager import HookManager, PhaseContext
from erickfp.provider.base import Provider
from erickfp.tools.read_file import ReadFileTool
from erickfp.tools.registry import ToolRegistry

_MAX_TURNS = 10
_SYSTEM_PROMPT = (
    "Eres un subagente de investigacion de solo lectura. Tu unica tool "
    "disponible es read_file -- no tienes bash ni write_file, ni forma "
    "alguna de escribir o ejecutar comandos. Lee lo que necesites y "
    "responde con una sintesis clara y breve de lo que encontraste."
)


def _read_only_registry() -> ToolRegistry:
    """Registry SUBSET con solo tools de lectura (Scenario 'Research solo
    tiene tools de lectura'): a diferencia del registry compartido del
    proceso (`tools/registry.py`), aqui `write_file`/`bash` JAMAS se
    registran."""
    registry = ToolRegistry()
    registry.register(ReadFileTool())
    return registry


class Research:
    """Subagente de investigacion (design.md D7): instancia un `Agent`
    acotado a tools de lectura, corre un turno completo con la tarea
    delegada como mensaje de usuario, y retorna el texto final."""

    def __init__(self, provider: Provider, hook_manager: HookManager | None = None) -> None:
        self.registry = _read_only_registry()
        allowed_tool_names = frozenset(
            tool.definition().name for tool in self.registry.all_tools()
        )
        ctx = PhaseContext(phase="research") if hook_manager is not None else None
        self._agent = Agent(
            provider,
            self.registry,
            self.registry.definitions(),
            hook_manager=hook_manager,
            ctx=ctx,
            policy=AllowList(allowed_tool_names),
            max_turns=_MAX_TURNS,
        )

    def run(self, task: str) -> str:
        """Ejecuta la tarea delegada como un turno completo del subagente y
        retorna el texto final concatenado (los bloques `text` del ultimo
        mensaje `assistant`)."""
        messages = [
            Message(
                role="user",
                content=[
                    Block(type="text", text=_SYSTEM_PROMPT),
                    Block(type="text", text=task),
                ],
            )
        ]
        result = self._agent.run_turn(messages)
        last_message = result[-1]
        return "\n".join(
            block.text for block in last_message.content if block.type == "text" and block.text
        )
