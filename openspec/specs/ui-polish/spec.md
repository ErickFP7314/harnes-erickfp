# UI Polish Specification

## Purpose

Identidad visual del harness: banner de portada precomputado y prompts decorados, ambos fieles a la paleta del tema (#00FFFF, #00FF00, fondo #222222).

## Requirements

### Requirement: Banner precomputado en build-time

El sistema MUST generar el asset del banner (`rich.text.Text` con estilos truecolor) a partir de `portada.html` en **build-time**. El runtime MUST NOT parsear HTML; solo MUST cargar el asset ya construido.

#### Scenario: Arranque muestra el banner desde el asset

- GIVEN el asset de banner ya generado en build-time
- WHEN el usuario ejecuta `erickfp chat`
- THEN el sistema renderiza el banner (25×149) dentro de un cuadro Rich, sin invocar ningún parser de HTML en tiempo de ejecución.

#### Scenario: Regeneración del asset

- GIVEN una actualización de `portada.html`
- WHEN se ejecuta el paso de build del asset
- THEN el nuevo asset refleja los cambios y el runtime lo consume sin recompilar en cada arranque.

### Requirement: Fallback adaptativo por ancho de terminal

El sistema MUST detectar el ancho de la terminal antes de renderizar el banner y MUST mostrar una versión reducida/alternativa legible cuando el ancho sea menor a 149 columnas.

#### Scenario: Terminal ancha (>=149 columnas)

- GIVEN una terminal con 149 columnas o más
- WHEN arranca la CLI
- THEN se renderiza el banner completo 25×149 en el cuadro.

#### Scenario: Terminal angosta (<149 columnas)

- GIVEN una terminal con menos de 149 columnas
- WHEN arranca la CLI
- THEN el sistema MUST renderizar una versión reducida o un Panel simple con el nombre del proyecto, sin cortar el arte a la mitad ni lanzar error.

### Requirement: Input decorado en cuadro

El prompt de entrada del usuario MUST mostrarse dentro de un cuadro Rich con bordes, respetando la paleta del tema.

#### Scenario: Prompt en cuadro con tema

- GIVEN una sesión de chat activa
- WHEN el sistema solicita el siguiente turno del usuario
- THEN el prompt se muestra dentro de un Panel con bordes, usando los colores cyan (#00FFFF) o verde (#00FF00) sobre fondo #222222, consistentes con el banner.

#### Scenario: Consistencia de tema entre banner e input

- GIVEN el banner ya renderizado con la paleta del tema
- WHEN se muestra el cuadro de input inmediatamente después
- THEN ambos elementos usan la misma paleta (#00FFFF/#00FF00/#222222), sin colores ad-hoc.
