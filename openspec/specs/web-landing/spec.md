# Web Landing Specification

## Purpose

Página principal (`WebPage/index.html`) que presenta ErickFP: qué es, en qué se diferencia, cómo se instala y qué features tiene, con estética terminal neón.

## Requirements

### Requirement: Hero con arte ASCII y one-liner

El hero MUST mostrar el arte ASCII de portada (generado por `web-portada-asset`), un one-liner que identifique a ErickFP como harness agéntico CLI gobernado por el método cartesiano, y al menos un CTA hacia instalación o guía.

#### Scenario: Primer viewport

- GIVEN un visitante que abre `index.html`
- WHEN carga la página
- THEN ve el arte de portada, el one-liner en español y un CTA visible sin hacer scroll (en desktop).

### Requirement: La idea y diferenciadores

La landing MUST incluir una sección que explique la idea del producto ("el modelo es el motor, el harness es todo lo demás" + Ciclo Cogito) y MUST presentar al menos 5 diferenciadores frente a otros harnesses (método cartesiano, trazabilidad ADR, gate default-deny + núcleo sagrado, provider-agnostic, free tier).

#### Scenario: Diferenciadores presentes

- GIVEN la sección "la idea"
- WHEN el visitante la lee
- THEN encuentra la explicación del producto y ≥5 diferenciadores identificables como ítems distintos.

### Requirement: Ciclo Cogito narrativo

La landing MUST presentar las 4 fases del Ciclo Cogito (duda → divide → ordena → enumera) como sección narrativa secuencial, con el comando asociado a cada fase.

#### Scenario: Recorrido de fases

- GIVEN la sección del Ciclo Cogito
- WHEN el visitante la recorre
- THEN ve las 4 fases en orden, cada una con su comando (`erickfp duda|divide|ordena|enumera`).

### Requirement: Tabs de instalación

La sección de instalación MUST ofrecer tabs por gestor: `npm` con badge explícito "coming soon" (MUST NOT presentarse como disponible) y `pip`, `uv` y `git clone` con comandos reales. Cada comando MUST ser copiable con un clic.

#### Scenario: Tab npm honesto

- GIVEN la sección de instalación
- WHEN el visitante selecciona el tab `npm`
- THEN ve el badge "coming soon" y ningún comando presentado como funcional.

#### Scenario: Copiar comando real

- GIVEN el tab `pip` activo
- WHEN el visitante pulsa el control de copiado
- THEN el comando completo queda en el portapapeles.

### Requirement: Demo terminal animada del permission gate

La landing MUST incluir una demo estilo terminal que reproduzca con efecto de tipeo una sesión `erickfp chat` culminando en el gate `¿aprobar? [y/n]` con respuesta `y`. El contenido de la demo MUST seguir siendo legible como texto si la animación no se ejecuta.

#### Scenario: Animación del gate

- GIVEN la demo visible en viewport
- WHEN se reproduce la animación
- THEN el visitante ve la secuencia tipearse hasta el prompt `[y/n]` y su aprobación.

#### Scenario: Sin JavaScript

- GIVEN un navegador con JS deshabilitado
- WHEN carga la página
- THEN la demo muestra su contenido como texto estático legible, sin romper el layout.

### Requirement: Grid de features completo

La landing MUST listar las 14 features del producto en un grid de cards: Ciclo Cogito, permission gate, PermissionPolicy pluggable, núcleo sagrado, grafo ADR, hooks por fase, provider-agnostic, tools + MCP, memoria persistente, compaction, subagentes, token viewer, UI terminal y calidad (TDD/capas).

#### Scenario: Cobertura total

- GIVEN el grid de features
- WHEN se cuentan las cards
- THEN las 14 features están presentes, cada una con título y descripción breve.

### Requirement: Comparativa vs otros harnesses

La landing MUST incluir una comparativa (estilo tabla con checkmarks) de ErickFP frente a otros harnesses, basada en los diferenciadores reales; MUST NOT atribuir capacidades falsas a terceros.

#### Scenario: Tabla comparativa

- GIVEN la sección comparativa
- WHEN el visitante la lee
- THEN ve a ErickFP contrastado en ≥4 dimensiones verificables.

### Requirement: Testimonios claramente ficticios

Los testimonios MUST presentarse como tweet-cards con nombres inventados y MUST indicar de forma visible que son ficticios (disclaimer en la sección o en el footer).

#### Scenario: Disclaimer visible

- GIVEN la sección de testimonios
- WHEN el visitante la ve
- THEN encuentra la indicación de que los testimonios son ficticios.

### Requirement: Navegación y footer

La landing MUST tener navegación fija/visible con enlaces a las secciones, a `guia.html` y al repositorio GitHub, y un footer con créditos y el disclaimer del sitio.

#### Scenario: Navegar a la guía

- GIVEN la navegación
- WHEN el visitante pulsa el enlace de la guía
- THEN llega a `guia.html` sin enlaces rotos.
