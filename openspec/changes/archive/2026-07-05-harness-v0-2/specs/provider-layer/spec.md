# Delta for Provider Layer

## ADDED Requirements

### Requirement: Retry configurable con backoff ante errores transitorios

El adapter MUST reintentar automáticamente ante errores 5xx o timeout del proveedor, con número de intentos y backoff configurables (por config, no hardcodeados). Al agotar los intentos, MUST propagar un `ProviderError` limpio en vez de la excepción nativa del SDK.

#### Scenario: Reintento exitoso tras 5xx transitorio

- GIVEN un adapter configurado con `attempts=3`
- WHEN la primera llamada falla con un error 5xx y la segunda tiene éxito
- THEN el adapter retorna la respuesta exitosa de la segunda llamada sin propagar error al llamador.

#### Scenario: Agotar intentos produce ProviderError limpio

- GIVEN un adapter configurado con `attempts=3` donde las 3 llamadas fallan con timeout
- WHEN se agotan los 3 intentos
- THEN el adapter lanza `ProviderError` con la causa registrada, y ningún tipo de excepción nativa del SDK cruza esa frontera.

#### Scenario: Errores no transitorios no se reintentan

- GIVEN un error de autenticación (4xx no reintentable) del proveedor
- WHEN ocurre en la primera llamada
- THEN el adapter NO reintenta y propaga `ProviderError` inmediatamente.

### Requirement: Exposición de uso de tokens y costo por turno

El adapter MUST exponer, tras cada respuesta, el conteo de tokens de entrada y salida del turno, para que la capa de token-viewer los acumule por sesión.

#### Scenario: Respuesta incluye conteo de tokens

- GIVEN una llamada exitosa al Provider
- WHEN el adapter traduce la respuesta a los tipos propios
- THEN el resultado incluye tokens de entrada y salida de ese turno, disponibles para el llamador.

## MODIFIED Requirements

### Requirement: Adapter LiteLLM hacia Gemini con continuidad de razonamiento

El adapter default MUST usar LiteLLM con `gemini/gemma-4-26b-a4b-it` como modelo default (ADR-001, decisión del usuario 2026-07-03 con evidencia empírica del spike 2.1), MUST permitir configurar otro modelo vía `set_model()`/constructor, MUST preservar las thought signatures del modelo a través de turnos múltiples, y MUST reintentar errores transitorios (5xx/timeout) con backoff configurable antes de propagar `ProviderError`.
(Previously: sin retry configurable; un solo intento antes de propagar el error del SDK.)

#### Scenario: Multi-turno preserva thought signature

- GIVEN una conversación de al menos dos turnos con tool use intermedio
- WHEN el adapter arma el siguiente request al modelo
- THEN incluye la thought signature del turno anterior sin descartarla
- AND el modelo no reporta pérdida de contexto de razonamiento en la respuesta.

#### Scenario: Retry preserva thought signature entre reintentos

- GIVEN un turno con thought signature previa que sufre un timeout transitorio
- WHEN el adapter reintenta la llamada
- THEN el reintento incluye la misma thought signature del turno anterior, sin perderla por el reintento.
