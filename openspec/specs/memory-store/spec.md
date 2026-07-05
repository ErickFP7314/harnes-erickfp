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

`Store.recall(...)` MUST permitir recuperar registros históricos específicos cuando el agente o el humano lo solicite explícitamente, sin cargarlos automáticamente en cada turno. Esta fase expone `recall` como una `Tool` registrada en el tool-registry, por lo que toda invocación de `recall` por el modelo MUST pasar por el permission gate como cualquier otra tool.
(Previously: `recall` solo se invocaba de forma interna/directa, sin pasar por el tool-registry ni por el gate.)

#### Scenario: Recall exitoso

- GIVEN registros previos guardados en el Store
- WHEN se invoca `Store.recall(query)` con un criterio que coincide
- THEN el sistema retorna los registros correspondientes.

#### Scenario: Recall como Tool pasa por el gate

- GIVEN `recall` registrada como Tool en el tool-registry
- WHEN el modelo emite un `tool_use` para `recall`
- THEN el permission gate evalúa la policy activa antes de ejecutar `Store.recall(...)`, igual que con `bash`/`read_file`/`write_file`.

### Requirement: Preamble de hechos de alto valor

`Store.preamble()` MUST cargarse automáticamente al iniciar `erickfp chat` o cualquier fase del ciclo, retornando los hechos de alto valor marcados como persistentes (p. ej. decisiones raíz), sin requerir invocación explícita del agente. Esta fase MUST enriquecer el preamble incorporando el resumen de fin de sesión más reciente cuando exista.
(Previously: preamble limitado a hechos marcados persistentes, sin incorporar el resumen de la sesión anterior.)

#### Scenario: Preamble presente al iniciar sesión

- GIVEN una sesión nueva de `erickfp chat`
- WHEN el sistema arranca
- THEN el contenido de `Store.preamble()` se incluye en el contexto inicial antes del primer turno del usuario.

#### Scenario: Preamble incluye resumen de la sesión anterior

- GIVEN un resumen de fin de sesión persistido en una sesión previa
- WHEN arranca una nueva sesión de `erickfp chat`
- THEN el preamble cargado incluye ese resumen junto con los hechos persistentes marcados.

### Requirement: Resumen de fin de sesión

Al salir del chat (`erickfp chat`), el sistema MUST generar y persistir un resumen de la sesión vía `Store.save(...)`, sin requerir invocación explícita del usuario.

#### Scenario: Resumen persistido al salir

- GIVEN una sesión de chat con al menos un turno completado
- WHEN el usuario termina la sesión (salida normal del REPL)
- THEN el sistema guarda un resumen de la sesión en el Store antes de finalizar el proceso.

#### Scenario: Sesión sin turnos no genera resumen vacío innecesario

- GIVEN una sesión que termina sin ningún turno completado
- WHEN el usuario sale del REPL
- THEN el sistema MAY omitir el resumen o guardar uno vacío explícito, sin fallar.
