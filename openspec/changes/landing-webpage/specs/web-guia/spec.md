# Web Guía Specification

## Purpose

Subpágina (`WebPage/guia.html`) con la guía de uso del producto, derivada de `docs/guia-de-uso.md`, navegable mediante sidebar.

## Requirements

### Requirement: Contenido derivado de la guía oficial

`guia.html` MUST cubrir el contenido de `docs/guia-de-uso.md`: qué es ErickFP, requisitos, instalación, `erickfp init`, `erickfp chat`, el ciclo completo (`duda`, `divide`, `ordena`, `enumera`) y troubleshooting. Los comandos y snippets MUST mostrarse en inglés tal como se ejecutan; el texto explicativo MUST estar en español.

#### Scenario: Cobertura de comandos

- GIVEN la subpágina de guía
- WHEN el visitante la recorre
- THEN encuentra documentados los 6 comandos: `init`, `chat`, `duda`, `divide`, `ordena`, `enumera`.

#### Scenario: Slash commands documentados

- GIVEN la sección de `erickfp chat`
- WHEN el visitante la lee
- THEN encuentra los slash commands del REPL: `/help`, `/model`, `/tools`, `/clear`, `/tokens`.

### Requirement: Sidebar de navegación

La guía MUST incluir un sidebar con enlaces ancla a todas sus secciones. En viewports angostos el sidebar MUST seguir siendo accesible (colapsado o reubicado) sin ocultar contenido de forma permanente.

#### Scenario: Salto por ancla

- GIVEN el sidebar visible
- WHEN el visitante pulsa el enlace de una sección
- THEN la vista se desplaza a esa sección y su encabezado queda visible.

#### Scenario: Sidebar en mobile

- GIVEN un viewport angosto (~360px)
- WHEN el visitante abre la guía
- THEN puede acceder a la navegación de secciones y leer el contenido completo sin scroll horizontal.

### Requirement: Snippets copiables

Los bloques de comandos de la guía MUST ser copiables con un clic, preservando el comando exacto.

#### Scenario: Copiar comando de la guía

- GIVEN un bloque con `erickfp duda "objetivo"`
- WHEN el visitante pulsa el control de copiado
- THEN el comando exacto queda en el portapapeles.

### Requirement: Coherencia con la landing

La guía MUST usar el mismo tema visual (`web-theme-terminal`) y MUST ofrecer navegación de regreso a `index.html`.

#### Scenario: Volver a la landing

- GIVEN la subpágina de guía
- WHEN el visitante pulsa el enlace al inicio
- THEN llega a `index.html` con el mismo tema visual, sin enlaces rotos.
