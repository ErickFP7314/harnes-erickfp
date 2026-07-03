# Spike 2.2 -- Límites free tier con tool calling

**Estado**: **BLOQUEADO -- misma causa raiz que el spike 2.1**: la
`GEMINI_API_KEY` del `.env` recien creado fue rechazada por Google con
`403 PERMISSION_DENIED: "Your API key was reported as leaked. Please use
another API key."` Ver `docs/spikes/thought-signature.md` para el detalle
completo y la accion requerida del usuario (revocar y reemplazar la key).

## Por que no se corrieron las 15 llamadas planificadas

El spike 2.1 (ejecutado primero, con la misma key) ya produjo evidencia
suficiente de que **ninguna llamada con esta key va a funcionar**: 3 de 4
modelos probados fueron rechazados con el mismo error 403 de key filtrada,
con latencias de rechazo de ~0.45-1.44s (rechazo rapido del lado de
Google, no un timeout ni un rate-limit). Ejecutar igual las 15 llamadas
secuenciales de `scripts/spike_free_tier_limits.py` no habria aportado
ningun dato nuevo sobre limites de RPM -- solo habria generado 15 rechazos
identicos contra una key ya marcada, lo cual ademas no es buena practica
de seguridad (seguir usando una credencial que el proveedor ya senalo como
comprometida). Se opto por **no ejecutar el script** hasta tener una key
valida.

**Ningun 429 (rate limit) fue observado** en ninguna de las 4 llamadas del
spike 2.1 -- todos los rechazos fueron 403 (key) o 404 (modelo), errores
de autenticacion/recurso, no de cuota. Esto significa que **todavia no
hay ningun dato real sobre el limite de RPM del free tier** -- ni siquiera
se llego a probar contra el limite, porque el bloqueo ocurrio un paso
antes (autenticacion).

## Plan de medicion (sigue vigente, sin cambios, pendiente de key nueva)

1. Cargar `GEMINI_API_KEY` nueva desde `.env`.
2. Disparar 15 llamadas secuenciales `litellm.completion(model="gemini/gemini-3-flash-preview", ..., tools=[...])`
   (15 > 10 RPM tipico del free tier, para forzar el limite dentro de la
   ventana de 1 minuto si existe).
3. Medir tiempo entre llamadas y contar cuantas se completan antes de un
   error de rate limit (429 o excepcion equivalente de litellm).
4. Comparar ese numero contra cuantas llamadas produce realmente un turno
   agentico corto del harness (duda: 1 llamada de texto -> posible
   `tool_use` -> `tool_result` -> respuesta final = 2-3 llamadas por turno
   logico de usuario).

## Mitigacion a documentar segun resultado

- Si el limite SI alcanza para un turno agentico tipico (2-3 llamadas):
  no se necesita mitigacion para el MVP -- YAGNI.
- Si NO alcanza: dos mitigaciones candidatas, a decidir por el usuario en un
  ADR aparte (no se decide aqui):
  - Backoff exponencial simple ante 429 en el adapter (`litellm_gemini.py`),
    con reintento acotado (p. ej. 3 intentos). Ya hay un prototipo de este
    patron en `scripts/spike_thought_signature.py::_call_with_backoff`
    (detecta "429"/"rate limit"/"RESOURCE_EXHAUSTED" en el mensaje de
    error y reintenta 1 vez tras 15s de espera).
  - Cache de respuestas para llamadas identicas dentro de una misma fase
    (bajo impacto esperado -- el patron conversacional rara vez repite
    prompts identicos).

## Que falta para desbloquear

1. Revocar la key actual reportada como filtrada y generar una nueva (ver
   `docs/spikes/thought-signature.md`, seccion "ACCION REQUERIDA DEL
   USUARIO").
2. Ejecutar `.venv/bin/python scripts/spike_free_tier_limits.py` con la key
   nueva.
3. Pegar aqui la tabla real de latencias/resultados y la conclusion final
   (alcanza / no alcanza + mitigacion elegida).
