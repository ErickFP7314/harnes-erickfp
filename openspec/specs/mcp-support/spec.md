# MCP Support Specification

## Purpose

Descubrimiento e invocación de tools remotas MCP (transports locales/stdio) tras la interfaz `Tool` existente, sin crear una ruta de ejecución paralela al gate/policy.

## Requirements

### Requirement: Tool MCP satisface la interfaz Tool existente

Cada tool remota MCP descubierta MUST adaptarse a la interfaz `Tool` (definición + `execute()`) ya definida en tool-registry, y MUST registrarse en el mismo registry que las tools locales.

#### Scenario: Tool MCP descubierta se registra como cualquier tool local

- GIVEN un servidor MCP local/stdio con al menos una tool expuesta
- WHEN el sistema arranca y descubre esa tool
- THEN la tool queda registrada en el tool-registry con una `ToolDef` válida, indistinguible en forma de las tools locales.

### Requirement: Mismo gate y policy que las tools locales

Una tool call sobre una tool MCP MUST pasar por el mismo permission gate y por la misma `PermissionPolicy` resuelta que cualquier tool local, sin ruta de ejecución alternativa.

#### Scenario: Tool MCP pasa por el gate

- GIVEN una tool MCP registrada
- WHEN el loop detecta un `tool_use` para esa tool
- THEN el gate consulta la policy activa y, de corresponder, pregunta y/n antes de invocar su `execute()`, igual que con `bash`/`read_file`/`write_file`.

#### Scenario: Transporte no soportado (edge, fuera de alcance)

- GIVEN una configuración MCP que declara un transport remoto no-stdio (p. ej. HTTP con OAuth)
- WHEN el sistema intenta descubrir sus tools
- THEN el sistema MUST rechazar la configuración con un error claro, sin intentar autenticación OAuth (fuera de alcance de esta fase).
