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

Toda tool call, sin excepción de tipo de tool o fase, MUST pasar por el permission gate implementado en la capa harness (no en la tool ni en el prompt del modelo). El gate MUST consultar la `PermissionPolicy` activa (default `AlwaysAsk`) antes de decidir si pregunta al humano; bajo `AlwaysAsk`, el comportamiento MUST ser idéntico al del ciclo 1: preguntar y/n, y el default ante respuesta vacía o ambigua MUST ser "no".
(Previously: el gate preguntaba y/n directamente sin capa de policy intermedia.)

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

- GIVEN cualquier tool registrada en el tool-registry (bash, read_file, write_file, o futuras, incluidas MCP)
- WHEN el loop detecta un bloque `tool_use` para esa tool
- THEN el sistema SHALL invocar el permission gate (con su policy resuelta) antes de invocar `execute()` de la tool, sin rutas alternativas de ejecución directa.

#### Scenario: PermissionPolicy AlwaysAsk preserva comportamiento del ciclo 1

- GIVEN `PermissionPolicy` sin configurar explícitamente (default `AlwaysAsk`)
- WHEN cualquier tool call llega al gate
- THEN el resultado observable (pregunta y/n, deny por defecto) es idéntico al del ciclo 1, sin regresión.

### Requirement: REPL despacha slash-commands antes del Provider

El REPL de `erickfp chat` MUST interceptar cualquier entrada que comience con `/` y despacharla al manejador de slash-commands (`/help`, `/model`, `/tools`, `/clear`, `/tokens`) sin invocar al Provider para ese turno.

#### Scenario: Entrada con "/" no llega al Provider

- GIVEN una sesión de chat activa
- WHEN el usuario escribe una entrada que comienza con `/`
- THEN el sistema resuelve el comando localmente y no realiza ninguna llamada al Provider en ese turno.

### Requirement: Tool desconocida en el registry

Si un bloque `tool_use` de la respuesta del Provider referencia un nombre de tool que NO está registrado en el tool-registry, el loop MUST NOT lanzar una excepción no controlada; MUST retornar un `tool_result` con `is_error=true` indicando tool desconocida, y el loop MUST continuar.

#### Scenario: Provider solicita una tool inexistente

- GIVEN una respuesta del Provider con un bloque `tool_use` cuyo nombre no coincide con ninguna tool registrada
- WHEN el loop procesa esa respuesta
- THEN el sistema retorna `tool_result` con `is_error=true` y un mensaje de "tool desconocida", sin invocar el permission gate ni lanzar excepción, y el ciclo continúa con el siguiente mensaje.
