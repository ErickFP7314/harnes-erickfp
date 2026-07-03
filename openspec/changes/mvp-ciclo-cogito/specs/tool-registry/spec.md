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

El registry MUST exponer las definiciones de tools (`ToolDef`) en un orden estable y determinístico entre invocaciones sucesivas del mismo proceso.

#### Scenario: Mismo orden en llamadas repetidas

- GIVEN un registry ya poblado con las 3 tools del MVP
- WHEN se solicita la lista de `ToolDef` dos veces en la misma sesión
- THEN ambas listas retornan las tools exactamente en el mismo orden.

#### Scenario: Nueva tool se añade al final

- GIVEN un registry con tools ya registradas
- WHEN se registra una tool adicional
- THEN la nueva tool SHOULD aparecer al final del orden existente, sin reordenar las anteriores.
