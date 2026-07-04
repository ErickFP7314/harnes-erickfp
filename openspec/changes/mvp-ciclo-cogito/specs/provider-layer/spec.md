# Provider Layer Specification

## Purpose

Interfaz propia que aísla al sistema de cualquier SDK nativo de LLM, permitiendo cambiar de proveedor sin tocar la lógica del agente.

## Requirements

### Requirement: Interfaz Provider agnóstica de SDK

El sistema MUST definir tipos propios (`Message`, `Block`, `ToolDef`, `Response`) que representen la intersección de las APIs soportadas. Ningún módulo fuera del adapter LiteLLM MUST importar SDKs nativos (`anthropic`, `openai`, `google-genai`).

#### Scenario: Aislamiento del SDK

- GIVEN el código fuente del paquete `erickfp`
- WHEN se inspeccionan los imports fuera de `src/erickfp/provider/adapters/litellm_adapter.py` (o equivalente)
- THEN ningún archivo importa `anthropic`, `openai` ni `google-genai` directamente.

#### Scenario: Tipos propios en la frontera

- GIVEN una llamada al Provider desde el agent-loop
- WHEN el adapter recibe la respuesta cruda de LiteLLM
- THEN el adapter la traduce a los tipos propios (`Response`, `Block`) antes de devolverla al llamador
- AND ningún tipo nativo del SDK cruza esa frontera.

### Requirement: Adapter LiteLLM hacia Gemini con continuidad de razonamiento

El adapter default MUST usar LiteLLM con `gemini/gemma-4-26b-a4b-it` como modelo default (ADR-001, decisión del usuario 2026-07-03 con evidencia empírica del spike 2.1; el literal original `gemini/gemini-3-flash` no está mapeado en litellm 1.83.7), MUST permitir configurar otro modelo vía `set_model()`/constructor, y MUST preservar las thought signatures del modelo a través de turnos múltiples.

#### Scenario: Multi-turno preserva thought signature

- GIVEN una conversación de al menos dos turnos con tool use intermedio
- WHEN el adapter arma el siguiente request al modelo
- THEN incluye la thought signature del turno anterior sin descartarla
- AND el modelo no reporta pérdida de contexto de razonamiento en la respuesta.
