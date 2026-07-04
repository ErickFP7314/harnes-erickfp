# Memory Store Specification

## Purpose

Interfaz de persistencia (`save`/`recall`/`preamble`) con implementación SQLite que conserva el historial de decisiones y sesiones del Ciclo Cogito.

## Requirements

### Requirement: Interfaz Store con impl SQLite

El sistema MUST definir una interfaz `Store` con métodos `save`, `recall` y `preamble`, e implementarla sobre SQLite en `.ErickFP/memory/`.

#### Scenario: Guardar una decisión de sesión

- GIVEN una fase del ciclo que produce una decisión relevante
- WHEN el sistema invoca `Store.save(...)`
- THEN el registro queda persistido en la base SQLite bajo `.ErickFP/memory/`.

### Requirement: Recall bajo demanda

`Store.recall(...)` MUST permitir recuperar registros históricos específicos cuando el agente o el humano lo solicite explícitamente, sin cargarlos automáticamente en cada turno.

#### Scenario: Recall exitoso

- GIVEN registros previos guardados en el Store
- WHEN se invoca `Store.recall(query)` con un criterio que coincide
- THEN el sistema retorna los registros correspondientes.

### Requirement: Preamble de hechos de alto valor

`Store.preamble()` MUST cargarse automáticamente al iniciar `erickfp chat` o cualquier fase del ciclo, retornando los hechos de alto valor marcados como persistentes (p. ej. decisiones raíz), sin requerir invocación explícita del agente.

#### Scenario: Preamble presente al iniciar sesión

- GIVEN una sesión nueva de `erickfp chat`
- WHEN el sistema arranca
- THEN el contenido de `Store.preamble()` se incluye en el contexto inicial antes del primer turno del usuario.
