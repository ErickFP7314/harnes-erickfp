# Agent Loop Specification

## Purpose

Bucle conversacional (`erickfp chat`) que conecta al humano con el Provider y ejecuta tools SOLO bajo consentimiento explícito, garantizando que ninguna tool call escape del gate de permisos.

## Requirements

### Requirement: Loop REPL con Provider

`erickfp chat` MUST ofrecer un REPL de texto plano que envía el turno del usuario al Provider, y si la respuesta contiene bloques `tool_use`, MUST pasar cada uno por el permission gate antes de ejecutarlo, repitiendo el ciclo hasta `end_turn`.

#### Scenario: Turno sin tool use

- GIVEN una sesión de chat activa
- WHEN el Provider responde solo con texto (sin `tool_use`)
- THEN el sistema muestra la respuesta y espera el siguiente turno del usuario, sin invocar el permission gate.

#### Scenario: Turno con una o más tool calls

- GIVEN una respuesta del Provider con bloques `tool_use`
- WHEN el loop procesa la respuesta
- THEN cada `tool_use` pasa individualmente por el permission gate antes de ejecutarse
- AND el resultado de cada tool (aprobado o negado) se anexa como `tool_result` en el siguiente mensaje al Provider.

### Requirement: Permission gate sin fuga

Toda tool call, sin excepción de tipo de tool o fase, MUST pasar por el permission gate implementado en la capa harness (no en la tool ni en el prompt del modelo). El gate MUST preguntar y/n al humano antes de ejecutar, y el default ante respuesta vacía o ambigua MUST ser "no".

#### Scenario: Aprobación explícita

- GIVEN una tool call pendiente de `bash`, `read_file` o `write_file`
- WHEN el humano responde "y"
- THEN el sistema ejecuta la tool y retorna su resultado real como `tool_result`.

#### Scenario: Negación explícita

- GIVEN una tool call pendiente
- WHEN el humano responde "n"
- THEN el sistema MUST NOT ejecutar la tool
- AND el sistema retorna un `tool_result` con `is_error=true` y un mensaje de negación
- AND el loop continúa sin lanzar ninguna excepción.

#### Scenario: Respuesta vacía o no reconocida (default deny)

- GIVEN una tool call pendiente
- WHEN el humano presiona Enter sin texto, o responde algo distinto de "y"/"n"
- THEN el sistema trata la respuesta como negación (default = no)
- AND retorna `tool_result` con `is_error=true`, igual que una negación explícita.

#### Scenario: Ninguna tool se ejecuta sin pasar por el gate

- GIVEN cualquier tool registrada en el tool-registry (bash, read_file, write_file, o futuras)
- WHEN el loop detecta un bloque `tool_use` para esa tool
- THEN el sistema SHALL invocar el permission gate antes de invocar `execute()` de la tool, sin rutas alternativas de ejecución directa.
