# Compaction Specification

## Purpose

Estrategia de compactación de historial (`CompactionStrategy`) que mantiene ventanas de contexto manejables sin romper jamás la integridad de un par `tool_use`/`tool_result`, y que vive como capa propia entre agent y provider — nunca dentro de `Provider.send`.

## Requirements

### Requirement: CompactionStrategy con sliding window y summarize

El sistema MUST definir `CompactionStrategy` como `typing.Protocol` con al menos dos estrategias: sliding window (descarta turnos antiguos) y summarize (resume turnos antiguos en un mensaje condensado). La compactación se MUST invocar desde la capa `agent`, nunca desde dentro de `Provider.send`.

#### Scenario: Historial excede el umbral configurado

- GIVEN una conversación cuyo historial supera el umbral de tokens/turnos configurado
- WHEN el agent-loop invoca `CompactionStrategy` antes del siguiente turno
- THEN el historial resultante es menor al original y conserva los turnos más recientes.

#### Scenario: Compaction nunca corre dentro de Provider.send

- GIVEN un turno en curso donde el adapter invoca `Provider.send`
- WHEN se inspecciona el call stack de esa invocación
- THEN ninguna llamada a `CompactionStrategy` ocurre dentro de `Provider.send`; la compactación, si aplica, ya ocurrió antes en la capa `agent`.

### Requirement: SafeSplitPoint nunca parte un par tool_use/tool_result

`SafeSplitPoint` MUST calcular el punto de corte de compactación de forma que NUNCA quede un bloque `tool_use` sin su `tool_result` correspondiente (o viceversa) en cualquiera de los dos segmentos resultantes. Este es un invariante formal: MUST NOT existir ningún corte válido que separe un par.

#### Scenario: Corte candidato cae dentro de un par tool_use/tool_result

- GIVEN un historial donde el corte candidato por umbral cae entre un `tool_use` y su `tool_result` correspondiente
- WHEN `SafeSplitPoint` calcula el punto real de corte
- THEN el sistema ajusta el corte hacia atrás, al límite del turno completo que contiene ambos bloques, manteniendo el par intacto en el mismo segmento.

#### Scenario: Ningún par roto tras compactar (invariante parametrizado)

- GIVEN múltiples historiales sintéticos con distintas posiciones de pares `tool_use`/`tool_result` y distintos umbrales de corte
- WHEN se aplica `SafeSplitPoint` a cada uno
- THEN en ningún caso el historial resultante contiene un `tool_use` sin su `tool_result` (ni un `tool_result` huérfano).

#### Scenario: Sin bloques tool_use pendientes

- GIVEN un historial sin ningún par `tool_use`/`tool_result` abierto
- WHEN se aplica compactación
- THEN el corte se aplica en el punto calculado por umbral sin ajustes adicionales.
