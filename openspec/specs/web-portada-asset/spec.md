# Web Portada Asset Specification

## Purpose

Pipeline build-time que convierte el arte ASCII de portada (`src/erickfp/ui/_portada_asset.py`, 25×149) en HTML consumible por la web, sin tocar el producto Python.

## Requirements

### Requirement: Generación build-time desde el asset

Un script en `WebPage/scripts/` MUST generar el HTML del arte leyendo `ROWS` de `src/erickfp/ui/_portada_asset.py`. El script MUST tratar el asset como solo lectura y MUST NOT modificar ningún archivo bajo `src/`. Las páginas del sitio MUST consumir el HTML ya generado: abrir el sitio MUST NOT requerir ejecutar el script ni ningún build.

#### Scenario: Generación del HTML

- GIVEN el asset `_portada_asset.py` presente
- WHEN se ejecuta el script de generación
- THEN se produce el HTML del arte en `WebPage/` y ningún archivo de `src/` cambia.

#### Scenario: Sitio abre sin build

- GIVEN el HTML del arte ya generado y versionado
- WHEN el visitante abre `index.html` en local (doble clic)
- THEN el arte se muestra sin ejecutar el script ni toolchain alguno.

### Requirement: Fidelidad del arte

El HTML generado MUST reproducir las 25 filas × 149 columnas del asset con los colores fg/bg exactos por celda, sin alterar caracteres ni introducir colores fuera de los presentes en el asset.

#### Scenario: Dimensiones y colores exactos

- GIVEN el HTML generado
- WHEN se compara contra `ROWS`
- THEN contiene 25 filas de 149 celdas y cada celda conserva su carácter y colores hex originales.

### Requirement: Comportamiento responsive del arte

El arte MUST permanecer legible y MUST NOT provocar scroll horizontal ni romper el layout en viewports angostos (hasta ~360px). El mecanismo concreto (escala fluida, versión recortada u otro) lo decide el design; este spec fija el comportamiento observable.

#### Scenario: Arte en mobile

- GIVEN un viewport de 360px
- WHEN se muestra el hero con el arte
- THEN el arte se percibe como composición coherente, sin scroll horizontal ni desbordes.

#### Scenario: Arte en desktop

- GIVEN un viewport ≥1280px
- WHEN se muestra el hero
- THEN el arte se ve completo (25×149) con proporciones estables.

### Requirement: Regenerabilidad

Re-ejecutar el script tras un cambio en el asset MUST regenerar el HTML de forma determinista, reflejando el nuevo arte sin ediciones manuales.

#### Scenario: Actualización del asset

- GIVEN una versión nueva de `_portada_asset.py`
- WHEN se re-ejecuta el script
- THEN el HTML resultante refleja el nuevo arte y sustituye limpiamente al anterior.
