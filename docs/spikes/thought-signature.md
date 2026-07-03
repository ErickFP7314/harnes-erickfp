# Spike 2.1 [OBLIGATORIO] -- Round-trip de thought signatures + comparativa Gemma

**Estado**: **CERRADO (2026-07-03) con evidencia empirica completa.**
Criterio de salida cumplido: mecanismo confirmado con llamadas reales y
desenlace en **ADR-001** (modelo default elegido por el usuario).

## Historial del bloqueo (resuelto)

La primera corrida (2026-07-03, mas temprano) fallo con
`403 PERMISSION_DENIED: "Your API key was reported as leaked"` -- Google
habia detectado la primera `GEMINI_API_KEY` como filtrada (se pego en texto
plano en un chat) y la desactivo del lado del servidor. El usuario genero
una key nueva y la corrida definitiva se hizo con ella. Leccion operativa
permanente: **las keys nunca viajan por el chat; se editan directo en
`.env` (gitignored, permisos 600)**. Registro completo del incidente en
engram: `config/gemini-api-key-status`.

Ese bloqueo dejo un hallazgo lateral valido: `gemini/gemma-3-27b-it` (el
alias que litellm 1.83.7 mapea) devuelve `404 NOT_FOUND` contra el endpoint
real `v1beta` -- **Gemma 3 no existe en el catalogo actual de la API**. Los
nombres reales de Gemma se obtuvieron consultando
`GET /v1beta/models?pageSize=1000`: `gemma-4-26b-a4b-it` y `gemma-4-31b-it`.

## Mecanismo confirmado (analisis estatico + confirmacion empirica)

Fuente estatica: codigo instalado de `litellm==1.83.7`.

- `litellm/litellm_core_utils/prompt_templates/factory.py:64` ->
  `THOUGHT_SIGNATURE_SEPARATOR = "__thought__"`.
- Para modelos Gemini, litellm **embebe la thought signature dentro del
  campo `id` del `tool_call`** (formato
  `"{id_original}__thought__{firma_base64}"`). Reenviar los mensajes con ese
  `id`/`tool_call_id` intacto hace que litellm reconstruya automaticamente
  el `thoughtSignature` del payload hacia Gemini. Para modelos no-Gemini,
  litellm elimina el sufijo (compatibilidad cross-provider).
- Para turnos de solo texto (sin `tool_use`), la firma viaja en
  `message.provider_specific_fields["thought_signatures"]`.

**Confirmacion empirica**: `scripts/spike_thought_signature.py` ejecuto 2
turnos reales de tool calling por modelo (turno 2 = reinyeccion del
`tool_call.id` tal cual + resultado de la tool). El turno 2 completo sin
error en los 5 modelos -- el round-trip funciona en la practica.

## Tabla comparativa final (llamadas reales, 2026-07-03)

| Modelo | Tools aceptado | Tool call parseable | Thought signature detectada | Turno 2 OK | Latencia t1/t2 | 429 |
|---|---|---|---|---|---|---|
| `gemini/gemini-3-flash-preview` | Si | Si | Si | Si | 13.53s / 12.54s | No |
| `gemini/gemini-flash-latest` | Si | Si | Si | Si | 1.89s / 1.91s | No |
| `gemini/gemini-3.5-flash` | Si | Si | Si | Si | 2.36s / 2.03s | No |
| `gemini/gemma-4-26b-a4b-it` | Si | Si | Si | Si | 3.77s / 8.76s | No |
| `gemini/gemma-4-31b-it` | Si | Si | Si | Si | 5.95s / 11.23s | No |

Notas:
- Los 5 modelos soportan el parametro `tools` estandar OpenAI via litellm y
  el mecanismo `__thought__` -- la asuncion arquitectonica mas fragil del
  design quedo validada.
- `gemini-3-flash-preview` funciona pero es notablemente mas lento
  (~13s/turno) que el resto.
- `gemini-flash-latest` es el mas rapido pero es un alias que Google
  re-apunta sin aviso (mala reproducibilidad).
- Los nombres Gemma 4 reales NO estan en `litellm.model_list` 1.83.7, pero
  litellm los acepta igual y los enruta correctamente (pass-through del
  nombre al endpoint).

## Desenlace: ADR-001 (decision del usuario, 2026-07-03)

**Modelo default del harness: `gemini/gemma-4-26b-a4b-it`.**

- Motivacion del usuario: preferencia por Gemma (modelo abierto) + cuotas
  free tier historicamente mas generosas.
- Trade-off aceptado y documentado: mas lento que `gemini-3.5-flash`
  (3.8s/8.8s vs 2.4s/2.0s), que era la recomendacion tecnica por velocidad
  y razonamiento.
- Siempre configurable via `set_model()`/constructor; el ADR fija solo el
  default.
- Implementado con TDD (RED->GREEN) en
  `src/erickfp/provider/litellm_gemini.py::DEFAULT_MODEL` y
  `tests/provider/test_litellm_gemini.py`.
- Registro en engram: `adr/001-modelo-default`.
