# Phase Hooks Specification

## Purpose

Motor de hooks (PreToolUse/PostToolUse/PhaseStart/PhaseEnd) que aplica restricciones determinísticas por fase, garantizando que el agente jamás pueda corromper el núcleo (`core/*`) y que el ciclo mantenga trazabilidad ADR.

## Requirements

### Requirement: Protección incondicional de `core/*`

Un hook PreToolUse MUST bloquear cualquier intento de escritura o modificación sobre `.ErickFP/core/Claude` o `.ErickFP/core/agents`, en cualquier fase del ciclo y en `erickfp chat`, sin importar si el permission gate fue aprobado por el humano.

#### Scenario: Escritura directa bloqueada

- GIVEN una tool call `write_file` cuyo path apunta dentro de `.ErickFP/core/`
- WHEN la tool call llega al hook PreToolUse, incluso después de que el humano respondió "y" en el permission gate
- THEN el hook bloquea la ejecución
- AND el sistema retorna `tool_result` con `is_error=true` y un mensaje indicando que `core/*` requiere una enmienda humana vía ADR.

#### Scenario: Bloqueo activo en toda fase y en chat

- GIVEN cualquier fase del Ciclo Cogito (`duda`, `divide`, `ordena`, `enumera`) o una sesión de `erickfp chat`
- WHEN se intenta escribir en `core/*` desde cualquiera de esos contextos
- THEN el hook de protección se aplica igual en todos, sin excepción por fase o comando.

#### Scenario: Escritura fuera de `core/*` no se bloquea por este hook

- GIVEN una tool call `write_file` fuera de `.ErickFP/core/`
- WHEN pasa por el hook de protección
- THEN el hook la deja continuar (sujeta solo al permission gate normal).

### Requirement: Trazabilidad ADR antes de síntesis

Un hook PreToolUse/PhaseStart en la fase `ordena` MUST validar que el artefacto de entrada referencia un nodo del grafo ADR (parent id). Si no encuentra la referencia, MUST bloquear el avance de la fase.

#### Scenario: Artefacto sin referencia ADR

- GIVEN el artefacto de `divide` sin campo de referencia a un nodo ADR padre
- WHEN se intenta iniciar `ordena`
- THEN el hook bloquea el inicio de la fase
- AND el sistema indica qué referencia falta.

### Requirement: Restricciones acumulativas por fase

Las restricciones activas de hooks previos MUST permanecer activas en las fases siguientes; una fase posterior nunca MUST relajar una restricción impuesta por una fase anterior.

#### Scenario: Acumulación entre `divide` y `ordena`

- GIVEN que el hook de protección de `core/*` está activo desde `duda`
- WHEN el ciclo avanza hasta `ordena` y se suma el hook de trazabilidad ADR
- THEN ambos hooks (protección `core/*` y trazabilidad ADR) están activos simultáneamente en `ordena`.
