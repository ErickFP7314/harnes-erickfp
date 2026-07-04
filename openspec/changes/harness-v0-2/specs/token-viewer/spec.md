# Token Viewer Specification

## Purpose

Contabilidad y reporte de tokens y costo estimado por sesión, vía el comando `/tokens`.

## Requirements

### Requirement: /tokens reporta uso y costo por sesión

El sistema MUST acumular tokens de entrada y salida por turno durante la sesión activa, y el comando `/tokens` MUST reportar el total acumulado junto con un costo estimado basado en el pricing conocido del modelo activo.

#### Scenario: Reporte con modelo de pricing conocido

- GIVEN una sesión con al menos un turno completado usando un modelo con pricing conocido
- WHEN el usuario escribe `/tokens`
- THEN el sistema muestra tokens de entrada, tokens de salida y costo estimado en la moneda configurada.

#### Scenario: Modelo sin pricing conocido

- GIVEN una sesión usando un modelo cuyo pricing no está registrado
- WHEN el usuario escribe `/tokens`
- THEN el sistema MUST reportar tokens acumulados normalmente y MUST mostrar el costo como "desconocido/0", sin lanzar error.

#### Scenario: /tokens antes del primer turno

- GIVEN una sesión recién iniciada sin turnos completados
- WHEN el usuario escribe `/tokens`
- THEN el sistema reporta 0 tokens y costo 0, sin error.
