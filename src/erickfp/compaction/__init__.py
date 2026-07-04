"""erickfp.compaction -- capa de estrategias de compactacion de historial.

Ubicada entre `erickfp.agent` y `erickfp.hooks|tools|provider|memory|ui` en
el contrato de capas (design.md, D5): `CompactionStrategy.compact` se invoca
al inicio de `run_turn`, antes del primer `provider.send`. Placeholder
creado en la tarea 1.2 (Lote 1, harness-v0-2); el codigo real llega en el
Lote 6.
"""

from __future__ import annotations
