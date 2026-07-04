# Ciclo Cogito Specification

## Purpose

Secuencia obligatoria de fases cartesianas (`duda → divide → ordena → enumera`) que gobierna el trabajo del agente mediante artefactos markdown encadenados, con soporte para modo interactivo y automático.

## Requirements

### Requirement: Fases secuenciales bloqueantes

Cada fase (`duda`, `divide`, `ordena`, `enumera`) MUST producir un artefacto markdown que sirva de entrada obligatoria a la fase siguiente. Una fase MUST NOT ejecutarse si el artefacto de la fase previa no existe.

#### Scenario: Cadena completa exitosa

- GIVEN un cambio nuevo sin artefactos previos
- WHEN el usuario ejecuta `duda`, luego `divide`, luego `ordena`, luego `enumera` en orden
- THEN cada comando produce su artefacto markdown
- AND cada fase consume el artefacto de la fase anterior como entrada.

#### Scenario: Fase bloqueante sin artefacto previo

- GIVEN que no existe el artefacto de `duda` para el cambio actual
- WHEN el usuario ejecuta `divide` directamente
- THEN el sistema falla limpiamente con un mensaje que indica la fase y el artefacto faltante
- AND el sistema MUST NOT crashear ni producir un artefacto parcial de `divide`.

### Requirement: `duda` exige claridad antes de avanzar

La fase `duda` (Evidencia) MUST evaluar si la especificación de entrada es clara y distinta. Si detecta ambigüedad, MUST negarse a producir el artefacto final y en su lugar solicitar clarificación al humano.

#### Scenario: Entrada ambigua

- GIVEN una descripción de cambio con requisitos contradictorios o incompletos
- WHEN se ejecuta `duda`
- THEN el sistema no genera el artefacto de `duda`
- AND responde con preguntas de clarificación específicas, sin avanzar a `divide`.

#### Scenario: Entrada clara y distinta

- GIVEN una descripción de cambio sin ambigüedad detectable
- WHEN se ejecuta `duda`
- THEN el sistema produce el artefacto `duda` marcando la evidencia como aceptada.

### Requirement: Modos y roles por fase

El ciclo MUST soportar modo interactivo (pausa entre fases) y modo automático (fases corren sin pausa), y MUST asignar el rol de `core/agents` correspondiente a cada fase (Planner en `duda`/`divide`, Coder en `ordena`, Reviewer en `enumera`).

#### Scenario: Modo interactivo pausa entre fases

- GIVEN el ciclo configurado en modo interactivo
- WHEN termina una fase
- THEN el sistema se detiene y espera confirmación del humano antes de iniciar la siguiente fase.

#### Scenario: Modo automático encadena sin pausa

- GIVEN el ciclo configurado en modo automático
- WHEN termina una fase con artefacto válido
- THEN el sistema inicia la siguiente fase inmediatamente sin esperar input adicional.
