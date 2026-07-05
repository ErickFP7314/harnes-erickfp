# Permission Policy Specification

## Purpose

Política de permisos pluggable (`PermissionPolicy`) intercalada entre el agent-loop y el tool-registry, sin debilitar jamás la robustez innegociable del gate ni del core_guard.

## Requirements

### Requirement: Interfaz PermissionPolicy con default AlwaysAsk

El sistema MUST definir `PermissionPolicy` como `typing.Protocol` con al menos tres implementaciones: `AlwaysAsk` (default), `AllowList`, `AskOnce`. El gate MUST consultar la policy activa antes de decidir si pregunta al humano.

#### Scenario: AlwaysAsk equivalente al gate del ciclo 1

- GIVEN `PermissionPolicy` sin configurar explícitamente (default `AlwaysAsk`)
- WHEN una tool call llega al gate
- THEN el comportamiento MUST ser idéntico al gate del ciclo 1: se pregunta y/n, solo "y" aprueba, cualquier otra respuesta (incluida vacía) es negación con `tool_result is_error=true`, sin excepciones.

#### Scenario: AllowList aprueba sin preguntar

- GIVEN una `AllowList` configurada con la tool `read_file` preaprobada
- WHEN llega una tool call de `read_file`
- THEN el gate ejecuta la tool sin preguntar al humano.

#### Scenario: AskOnce pregunta una sola vez por sesión

- GIVEN `AskOnce` activa y la tool `bash` sin decisión previa en la sesión
- WHEN llega la primera tool call de `bash`
- THEN el gate pregunta y/n; decisiones subsecuentes de `bash` en la misma sesión usan la respuesta registrada sin volver a preguntar.

### Requirement: core_guard prevalece sobre cualquier policy

Ninguna implementación de `PermissionPolicy` (incluidas `AllowList` y `AskOnce`) MUST NOT poder aprobar automáticamente una escritura en `.ErickFP/core/*`. El core_guard MUST evaluarse por encima de la policy resuelta, sin excepción.

#### Scenario: AllowList no cubre escrituras en core

- GIVEN una `AllowList` que preaprueba `write_file` en general
- WHEN llega una tool call de `write_file` cuyo target cae bajo `.ErickFP/core/*`
- THEN el core_guard MUST intervenir (bloqueo o pregunta reforzada) sin que la policy la apruebe automáticamente.

#### Scenario: AskOnce no memoriza aprobación sobre core

- GIVEN `AskOnce` con una aprobación previa registrada para `write_file` en general
- WHEN una nueva tool call de `write_file` apunta a `.ErickFP/core/*`
- THEN el sistema MUST re-evaluar vía core_guard, ignorando la memoria de `AskOnce` para ese target.

### Requirement: Negación por defecto sin excepción, bajo cualquier policy

Ante respuesta vacía o ambigua del humano cuando la policy sí pregunta, el resultado MUST ser negación (`tool_result is_error=true`), igual bajo `AlwaysAsk`, `AllowList` (en su rama de pregunta) o `AskOnce`.

#### Scenario: Respuesta ambigua bajo AskOnce

- GIVEN `AskOnce` preguntando por primera vez en la sesión
- WHEN el humano responde algo distinto de "y"/"n"
- THEN el sistema trata la respuesta como negación y NO la registra como aprobación futura.
