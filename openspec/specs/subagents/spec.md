# Subagents Specification

## Purpose

`Agent` reutilizable que permite instanciar subagentes acotados; `Research` es el subagente read-only entregado en esta fase, invocado vía la tool `delegate`.

## Requirements

### Requirement: Agent reutilizable y subagente Research read-only

El sistema MUST refactorizar `Agent` para ser instanciable con un subconjunto de tools. El subagente `Research` MUST instanciarse SOLO con tools de lectura (p. ej. `read_file`), y MUST NOT tener acceso a tools de escritura (`write_file`) ni a `bash` con efectos de escritura.

#### Scenario: Research solo tiene tools de lectura

- GIVEN la tool `delegate` invocada con el rol `research`
- WHEN se instancia el subagente
- THEN su tool-registry local contiene únicamente tools de solo lectura, y `write_file` no está registrada.

#### Scenario: Research no puede escribir

- GIVEN un subagente `Research` en ejecución
- WHEN el modelo dentro del subagente intenta invocar una tool de escritura
- THEN la tool no existe en su registry y la invocación falla como tool desconocida, sin ejecutar ninguna escritura.

### Requirement: Aprobación del delegate cubre las tool calls del subagente, core_guard sigue activo

Las tool calls individuales ejecutadas DENTRO de un subagente delegado MUST NOT requerir una aprobación adicional del humano más allá de la aprobación ya otorgada a la tool call `delegate` que lo instanció. Sin embargo, el core_guard MUST seguir evaluándose dentro del subagente para cualquier operación que lo dispare.

#### Scenario: Tool calls internas del subagente no piden aprobación individual

- GIVEN el humano aprobó la tool call `delegate` con rol `research`
- WHEN el subagente ejecuta múltiples llamadas a `read_file` internamente
- THEN ninguna de esas llamadas internas dispara una nueva pregunta y/n al humano.

#### Scenario: core_guard bloquea escritura en core incluso dentro del subagente

- GIVEN un subagente en ejecución (hipotéticamente con acceso a `write_file` en una configuración futura)
- WHEN se intenta una escritura bajo `.ErickFP/core/*` desde dentro del subagente
- THEN el core_guard MUST seguir bloqueando/evaluando esa escritura igual que en el agente principal, sin bypass por estar dentro de un subagente.
