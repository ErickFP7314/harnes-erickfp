# Spike 2.2 -- Límites free tier con tool calling

**Estado**: **CERRADO (2026-07-03) con medicion real.** Ejecutado con la
key nueva y el modelo del ADR-001 (`gemini/gemma-4-26b-a4b-it`).

## Historial

La primera corrida quedo bloqueada por la key reportada como filtrada
(mismo incidente que el spike 2.1 -- ver
`docs/spikes/thought-signature.md`, seccion "Historial del bloqueo"). Con
la key nueva se ejecuto el plan de medicion completo.

## Resultado de la medicion real

`scripts/spike_free_tier_limits.py`: 15 llamadas secuenciales
`litellm.completion(model="gemini/gemma-4-26b-a4b-it", ..., tools=[...])`
para forzar el limite de 10 RPM dentro de la ventana de 1 minuto si
existiera.

- **10/10 llamadas consecutivas OK, ningun 429 observado.** La latencia
  propia del modelo (~3-13s por llamada; t=169s acumulado en la llamada 10)
  mantiene el ritmo efectivo por debajo de 10 RPM de forma natural -- el
  free tier NUNCA llego a ser el cuello de botella.
- La llamada 11 fallo con **`500 INTERNAL` transitorio del servidor** (no
  es un error de cuota ni de key). Tipico de modelos recien publicados como
  Gemma 4.

## Conclusion

1. **El free tier alcanza sin mitigacion de cuota para el MVP**: un turno
   agentico tipico (2-3 llamadas por turno logico) cabe holgadamente --
   YAGNI sobre backoff-por-429 y cache.
2. **Mitigacion SI requerida (nueva, no prevista)**: reintento con backoff
   acotado ante **500/INTERNAL esporadicos** en el adapter
   (`litellm_gemini.py`). Prototipo del patron ya existe en
   `scripts/spike_thought_signature.py::_call_with_backoff` (extender su
   deteccion de "429" a "500"/"INTERNAL"). Anotado para la Fase 11
   (integracion y robustez) en tasks.md.
