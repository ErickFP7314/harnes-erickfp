# CLI Init Specification

## Purpose

Comando de arranque que materializa la estructura de gobierno `.ErickFP/` (núcleo cartesiano + grafo ADR) necesaria para que el resto del sistema opere.

## Requirements

### Requirement: Scaffolding de `.ErickFP/`

El comando `erickfp init` MUST generar el árbol `.ErickFP/{core/Claude, core/agents, adr/, memory/, hooks/}` con las plantillas raíz provistas por el proyecto.

#### Scenario: Primera inicialización

- GIVEN un repositorio sin `.ErickFP/`
- WHEN el usuario ejecuta `erickfp init`
- THEN el sistema crea `.ErickFP/core/Claude`, `.ErickFP/core/agents`, `.ErickFP/adr/`, `.ErickFP/memory/`, `.ErickFP/hooks/`
- AND cada plantilla raíz queda poblada con su contenido base (no vacía).

#### Scenario: Re-inicialización sobre estructura existente

- GIVEN un repositorio con `.ErickFP/` ya existente y con contenido modificado por el humano
- WHEN el usuario ejecuta `erickfp init` de nuevo
- THEN el sistema MUST NOT sobrescribir `core/Claude` ni `core/agents` sin confirmación explícita del humano
- AND el sistema informa qué rutas ya existían y cuáles fueron creadas.

### Requirement: Trazabilidad ADR desde el origen

La estructura generada MUST incluir el directorio `adr/` listo para recibir archivos markdown con frontmatter (`id`, `parents`, `estado`, `trade-off`), de modo que toda decisión futura pueda anclarse a un nodo raíz.

#### Scenario: Directorio ADR vacío pero válido

- GIVEN una inicialización recién completada
- WHEN se inspecciona `.ErickFP/adr/`
- THEN el directorio existe y SHOULD contener un README o plantilla de ejemplo con el formato de frontmatter esperado.
