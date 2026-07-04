"""erickfp.subagents -- capa de subagentes (Research, DelegateTool).

Ubicada POR ENCIMA de `erickfp.agent` en el contrato de capas (design.md,
seccion "Ciclo delegate"): `DelegateTool`/`Research` construyen un `Agent`
(capa agent) + subset del registry (capa tools); si vivieran en `tools/`
cerrarian el ciclo tool->subagent->agent->tool. Se registran desde el
composition root (`cli.py`); `tools/` nunca importa `agent`/`subagents`.
Placeholder creado en la tarea 1.2 (Lote 1, harness-v0-2); el codigo real
llega en el Lote 7.
"""

from __future__ import annotations
