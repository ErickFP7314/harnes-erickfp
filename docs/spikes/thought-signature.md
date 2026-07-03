# Spike 2.1 [OBLIGATORIO] -- Round-trip de thought signatures + comparativa Gemma

**Estado**: **BLOQUEADO -- CRITICO DE SEGURIDAD**. Se ejecutaron las 4
llamadas reales pedidas (`gemini/gemini-3-flash-preview`,
`gemini/gemini-flash-latest`, `gemini/gemini-3.5-flash`,
`gemini/gemma-3-27b-it`) contra la API real de Google con la
`GEMINI_API_KEY` del `.env` recien creado. **Google rechazo la key con
`403 PERMISSION_DENIED: "Your API key was reported as leaked. Please use
another API key."` en 3 de los 4 modelos probados.** Esto NO es un
problema de codigo, de LiteLLM ni de este harness -- es que Google ya
detecto y marco esta key especifica como filtrada/expuesta publicamente, y
la desactivo del lado del servidor. Ninguna llamada con esta key va a
funcionar hasta que se reemplace.

**No se ejecuto el spike 2.2** (free-tier limits) mas alla de esta
evidencia -- continuar disparando llamadas contra una key ya marcada como
filtrada no aporta datos utiles y no es buena practica. Ver
`docs/spikes/free-tier-limits.md`.

**Nunca se imprimio ni logueo el valor de la key** -- solo se verifico su
presencia (`bool`) y longitud (39 caracteres) antes de usarla; los mensajes
de error de Google tampoco contienen la key.

## ACCION REQUERIDA DEL USUARIO (antes de continuar cualquier spike/fase que use la API real)

1. **Revocar esta key ya mismo** en Google AI Studio / Google Cloud Console
   (es probable que Google ya la haya desactivado del lado del servidor,
   pero debe revocarse explicitamente para evitar reactivaciones).
2. **Investigar el origen de la fuga**: Google no dice donde la detecto,
   pero las causas tipicas son: la key quedo commiteada en un repo git
   (publico o que se sincronizo/escaneo), se pego en un canal publico
   (issue, gist, foro, chat compartido), o quedo en un archivo que se subio
   sin querer. Vale la pena revisar el historial de git de este repo y de
   cualquier otro lugar donde se haya pegado la key (aunque este `.env` esta
   bien gitignored y con permisos 600, la fuga pudo ser anterior a crear
   este archivo).
3. Generar una **key nueva** y colocarla en `.env` (`GEMINI_API_KEY=...`,
   permisos 600, ya gitignored).
4. Re-ejecutar `scripts/spike_thought_signature.py` y
   `scripts/spike_free_tier_limits.py` con la key nueva.

## Evidencia empirica real (con la key marcada como filtrada)

| Modelo | Llamada 1 (texto+tools) | Codigo/mensaje de error real de Google |
|---|---|---|
| `gemini/gemini-3-flash-preview` | Rechazada | `403 PERMISSION_DENIED`: "Your API key was reported as leaked." |
| `gemini/gemini-flash-latest` | Rechazada | `403 PERMISSION_DENIED`: "Your API key was reported as leaked." |
| `gemini/gemini-3.5-flash` | Rechazada | `403 PERMISSION_DENIED`: "Your API key was reported as leaked." |
| `gemini/gemma-3-27b-it` | Rechazada (error distinto) | `404 NOT_FOUND`: `models/gemma-3-27b-it is not found for API version v1beta, or is not supported for generateContent` |

Latencias observadas (no son de rate-limit, son de rechazo rapido):
`gemini-3-flash-preview` 1.44s, `gemini-flash-latest` 1.29s,
`gemini-3.5-flash` 0.45s, `gemma-3-27b-it` 1.26s. Ningun 429 (el bloqueo es
por la key, no por cuota).

**Nota sobre el 404 de `gemma-3-27b-it`**: es un error DISTINTO al 403 de
"leaked key" de los otros tres -- sugiere que para ese modelo la
autenticacion si paso una validacion previa (o el orden de validaciones de
Google evalua primero si el modelo soporta `generateContent`), y el error
real es que el nombre de modelo `gemma-3-27b-it` (tal como litellm lo
resuelve para el proveedor `gemini/`, es decir contra el endpoint
`v1beta` de Google AI Studio, no Vertex) no existe ahi para ese metodo.
Esto es un hallazgo independiente y valido pese al bloqueo de la key: **el
alias `gemini/gemma-3-27b-it` de litellm no resuelve correctamente contra
el endpoint real de Google AI Studio (v1beta)** -- posible desalineamiento
entre el registro estatico de litellm y el catalogo real de modelos
expuestos por ese endpoint. A reverificar con una key valida.

## Analisis estatico previo (sigue siendo valido -- no depende de la key)

Todo lo de esta seccion viene de leer el codigo fuente instalado de
`litellm==1.83.7` (no de las llamadas reales, que fallaron por la key):

- `litellm/litellm_core_utils/prompt_templates/factory.py:64` ->
  `THOUGHT_SIGNATURE_SEPARATOR = "__thought__"`.
- `litellm/utils.py` (~l.668-750): para modelos Gemini, litellm **embebe la
  thought signature dentro del campo `id` del `tool_call`** devuelto
  (formato `"{id_original}__thought__{firma_base64}"`). Al reenviar los
  mismos mensajes (con ese `id`/`tool_call_id` intacto) en el turno
  siguiente, litellm reconstruye automaticamente el campo
  `thoughtSignature` del payload saliente hacia Gemini. Si el modelo
  destino NO es Gemini, litellm **elimina** ese sufijo del id antes de
  enviarlo (compatibilidad cross-provider).
- `litellm/llms/vertex_ai/gemini/transformation.py` (~l.440-500): para
  turnos de **solo texto** (sin `tool_use`), la firma viaja en
  `message.provider_specific_fields["thought_signatures"]` (lista) -- el
  campo que el adapter debe leer y reinyectar para ese caso.
- **Este mecanismo sigue siendo la mejor hipotesis de diseno para Fase 4**
  (tareas 4.5/4.6), pero **AUN NO esta confirmado con una llamada real
  exitosa** -- eso requiere la key nueva.

### Hallazgo -- modelo default `gemini/gemini-3-flash` no mapeado en litellm

`litellm.get_model_info("gemini/gemini-3-flash")` sigue devolviendo
`"This model isn't mapped yet"` en litellm 1.83.7. Alias SI mapeados:
`gemini/gemini-3-flash-preview`, `gemini/gemini-flash-latest`,
`gemini/gemini-3.5-flash`, `gemini/gemini-3.1-flash-lite`. Con la key
filtrada no se pudo determinar cual de estos responde realmente -- todos
fueron rechazados por el mismo motivo (la key, no el modelo).

## Comparativa Gemma (ampliacion pedida por el usuario, 2026-07-03)

Investigacion previa del usuario: Gemma 3 no tiene function calling nativo
en la Gemini API (solo prompt-based, parseo de `tool_code`); Gemma 4
documenta tools por JSON schema pero no verificado via LiteLLM.

**Tabla comparativa final** (columnas empiricas = "N/D (key filtrada)"
donde el bloqueo de la key impidio observar el comportamiento real; la
unica fila con un dato empirico distinto al bloqueo de key es
`gemma-3-27b-it`, que dio 404 de modelo no encontrado):

| Modelo | Responde en free tier | Tools nativo | Thought signatures round-trip | Latencia (rechazo) | Veredicto |
|---|---|---|---|---|---|
| `gemini/gemini-3-flash-preview` | N/D -- bloqueado por key filtrada (403) | Se espera SI (metadata litellm: `supports_function_calling=true`) | N/D -- bloqueado, mecanismo `__thought__` sigue sin confirmar empiricamente | 1.44s (rechazo) | Candidato principal, pendiente re-test con key nueva |
| `gemini/gemini-flash-latest` | N/D -- bloqueado por key filtrada (403) | Se espera SI | N/D -- bloqueado | 1.29s (rechazo) | Candidato alterno, pendiente re-test |
| `gemini/gemini-3.5-flash` | N/D -- bloqueado por key filtrada (403) | Se espera SI | N/D -- bloqueado | 0.45s (rechazo) | Candidato alterno, pendiente re-test |
| `gemini/gemma-3-27b-it` | **NO -- 404, el alias no resuelve contra el endpoint v1beta real**, independiente de la key | No verificable (nunca llego a la etapa de tools) | No aplica (no hay `thinking` con firma en Gemma) | 1.26s (rechazo) | **Descartado tal como esta mapeado hoy en litellm** -- requeriria investigar el nombre de modelo correcto en el catalogo real de Google AI Studio, no solo confiar en `litellm.model_list` |
| Gemma 4 (via `gemini/`) | No evaluable | N/A | N/A | N/A | Fuera de alcance -- no existe ningun modelo `gemma-4*` bajo el proveedor `gemini/` en litellm 1.83.7 |

## Recomendacion (evidencia, no decision -- ADR pendiente para el usuario)

Con los datos disponibles hasta ahora (bloqueados en su mayoria por la key
filtrada), la recomendacion **no cambia respecto al analisis estatico**,
pero sigue **sin confirmacion empirica real**:

- Mantener **Gemini 3 Flash** (uno de los 3 alias mapeados,
  probablemente `gemini-3-flash-preview` por ser el nombre mas cercano al
  literal del design) como modelo default, PERO esto debe confirmarse con
  una llamada real exitosa antes de fijarlo en el adapter (Fase 4, tarea
  4.4) -- todavia no hay ninguna prueba de que el mecanismo de thought
  signature funcione en la practica, solo la hipotesis del analisis
  estatico del codigo de litellm.
- `gemini/gemma-3-27b-it`, tal como esta mapeado hoy en litellm 1.83.7,
  **no resuelve contra el endpoint real** (404) -- se recomienda **no
  usarlo como esta** ni siquiera como fallback economico hasta encontrar el
  nombre de modelo correcto en el catalogo real de Google AI Studio (esto
  es independiente del problema de la key).
- Gemma 4 sigue fuera de alcance.

**La decision final de modelo default sigue pendiente como ADR para el
usuario** -- este documento aporta evidencia (ahora parcialmente
empirica), no la toma. El bloqueo de la key impide cerrar esta
recomendacion con confianza total.

## Que falta para desbloquear (actualizado)

1. **Revocar la key actual y generar una nueva** (ver seccion "ACCION
   REQUERIDA DEL USUARIO" arriba) -- esto es lo unico que falta, el script
   y el analisis ya estan completos.
2. Re-ejecutar `.venv/bin/python scripts/spike_thought_signature.py` con la
   key nueva.
3. Sustituir las celdas "N/D (key filtrada)" de la tabla comparativa por
   los datos empiricos reales (tools OK, tool_call recibido, thought
   signature detectada, turno 2 OK).
4. Investigar por separado el nombre de modelo correcto para Gemma 3 en el
   endpoint real de Google AI Studio (el 404 de `gemma-3-27b-it` es
   independiente del problema de la key y debe resolverse aparte).
5. Con datos empiricos completos, confirmar o ajustar el alias exacto de
   "Gemini 3 Flash" antes de implementar `src/erickfp/provider/litellm_gemini.py`
   (tarea 4.4).
