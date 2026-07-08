# Web Theme Terminal Specification

## Purpose

Sistema visual compartido por todas las páginas de `WebPage/`: paleta terminal neón fiel a `theme.py`, tipografía monospace, responsive y accesibilidad básica.

## Requirements

### Requirement: Paleta exacta del tema

El tema MUST definir como tokens centralizados la paleta de `theme.py`: cyan `#00FFFF`, verde `#00FF00`, fondo `#222222`, más sus rampas (familia cyan `#00E6E6`–`#B3FFFF`, familia verde `#00E600`–`#99FF99`) y blanco `#FFFFFF`. Los colores de acento usados en las páginas MUST provenir de estos tokens; MUST NOT introducirse colores de acento ad-hoc fuera de la paleta.

#### Scenario: Acentos desde tokens

- GIVEN los estilos del sitio
- WHEN se inspeccionan los colores de acento de landing y guía
- THEN todos resuelven a tokens de la paleta definida, sobre fondo `#222222`.

### Requirement: Tipografía monospace

Todo el texto del sitio MUST renderizarse con una familia monospace con fallbacks del sistema, coherente con la estética terminal.

#### Scenario: Fuente consistente

- GIVEN cualquier página del sitio
- WHEN se renderiza el texto (títulos, cuerpo, snippets)
- THEN la familia efectiva es monospace en todos los elementos.

### Requirement: Neón solo en acentos

El neón (cyan/verde a plena saturación) MUST reservarse para acentos: títulos, enlaces, elementos interactivos y detalles. El texto base de lectura MUST usar un gris claro de la paleta, MUST NOT ser cyan o verde puro en bloques largos.

#### Scenario: Párrafo largo legible

- GIVEN una sección con varios párrafos de texto
- WHEN el visitante la lee
- THEN el cuerpo del texto es gris claro y solo los acentos usan neón.

### Requirement: Responsive

Las páginas MUST ser usables desde viewports de ~360px hasta desktop ancho: sin scroll horizontal, sin contenido cortado y con controles alcanzables.

#### Scenario: Viewport mobile

- GIVEN un viewport de 360px de ancho
- WHEN se carga cualquier página del sitio
- THEN no aparece scroll horizontal y todas las secciones son legibles.

#### Scenario: Viewport desktop

- GIVEN un viewport ≥1280px
- WHEN se carga la landing
- THEN el contenido se presenta con un ancho máximo controlado, sin líneas de texto desmesuradas.

### Requirement: Accesibilidad básica

El sitio MUST cumplir: contraste suficiente del texto base sobre `#222222` (orientado a WCAG AA), texto alternativo o rol adecuado en imágenes y arte decorativo, HTML semántico (landmarks `header/nav/main/footer`, jerarquía de headings sin saltos) y foco visible en elementos interactivos.

#### Scenario: Navegación por teclado

- GIVEN un usuario navegando con Tab
- WHEN recorre enlaces, tabs y botones de copiado
- THEN cada elemento interactivo recibe foco visible y es operable con teclado.

#### Scenario: Estructura semántica

- GIVEN el HTML de cualquier página
- WHEN se inspecciona su estructura
- THEN existen landmarks semánticos y una jerarquía de headings ordenada (un solo `h1` por página).
