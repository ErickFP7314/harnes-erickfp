# Tool Registry Specification

## Purpose

Registro central de tools con orden estable de definiciones, base para el permission gate y para futuras optimizaciones de prompt caching.

## Requirements

### Requirement: Interfaz Tool y registro

El sistema MUST definir una interfaz `Tool` (definición + `execute()`) y un registry que permita registrar `bash`, `read_file` y `write_file` en el MVP.

#### Scenario: Registro de las 3 tools del MVP

- GIVEN el arranque del sistema
- WHEN el registry se inicializa
- THEN `bash`, `read_file` y `write_file` quedan registradas y disponibles para el loop.

### Requirement: Orden estable de definiciones

El registry MUST exponer las definiciones de tools (`ToolDef`) en un orden estable y determinístico entre invocaciones sucesivas del mismo proceso. Registrar tools remotas MCP MUST NOT reordenar las tools locales ya existentes.
(Previously: el orden estable solo se garantizaba entre tools locales del MVP.)

#### Scenario: Mismo orden en llamadas repetidas

- GIVEN un registry ya poblado con las 3 tools del MVP
- WHEN se solicita la lista de `ToolDef` dos veces en la misma sesión
- THEN ambas listas retornan las tools exactamente en el mismo orden.

#### Scenario: Nueva tool se añade al final

- GIVEN un registry con tools ya registradas
- WHEN se registra una tool adicional
- THEN la nueva tool SHOULD aparecer al final del orden existente, sin reordenar las anteriores.

#### Scenario: Tool MCP se añade al final sin reordenar las locales

- GIVEN un registry con `bash`, `read_file` y `write_file` ya registradas en ese orden
- WHEN se registra una tool MCP descubierta
- THEN la tool MCP aparece al final del orden, y `bash`, `read_file`, `write_file` conservan su orden relativo original.

### Requirement: Registro de tools remotas MCP junto a las locales

El registry MUST permitir registrar tools remotas MCP (adaptadas a la interfaz `Tool` existente) junto a las tools locales, usando el mismo mecanismo de registro y sin requerir un registry separado.

#### Scenario: Tool MCP se registra en el mismo registry

- GIVEN el tool-registry ya poblado con `bash`, `read_file` y `write_file`
- WHEN se descubre y registra una tool MCP
- THEN la tool MCP queda disponible en el mismo registry, consultable junto con las tools locales.
