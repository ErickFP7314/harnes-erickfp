# Claude -- Axiomas de ErickFP (Nodo Raiz)

Este archivo es el nodo raiz semantico del grafo ADR (`.ErickFP/adr/`):
ninguna decision tecnica puede contradecir lo escrito aqui sin abrir primero
un ADR de tipo `amendment` que lo referencie explicitamente.

## Axiomas inmutables

1. **Legibilidad antes que Extensibilidad, y Extensibilidad antes que
   Rendimiento.** El codigo generado por los agentes debe ser legible por un
   humano antes que optimo o generico.
2. **Ningun agente actua sin consultar la raiz.** Toda fase del Ciclo Cogito
   (`duda` -> `divide` -> `ordena` -> `enumera`) y el modo `chat` cargan
   este archivo y `core/agents/` como parte de su contexto de sistema antes
   de razonar o responder.
3. **El agente nunca escribe en `core/*` sin consentimiento humano
   explicito.** El hook `core_guard` hace cumplir este axioma en tiempo de
   ejecucion, incluso si el permission gate ya aprobo la accion.
4. **Toda decision tecnica traza hasta este archivo.** El grafo ADR usa este
   archivo como raiz semantica: cada ADR sin padres (`parents: []`) debe
   justificar por que es un axioma derivado de este documento.

## Trade-offs arquitectonicos aceptados

- Se prioriza la legibilidad del harness sobre la concision -- comentarios y
  nombres explicitos son bienvenidos aunque alarguen el archivo.
- Se prioriza la extensibilidad (Protocols estructurales, registry de
  tools) sobre la simplicidad de un monolito, siempre que exista una
  segunda implementacion real que lo justifique (YAGNI por etapa).

> Puedes (y debes) editar este archivo para reflejar los axiomas de TU
> proyecto. Los agentes de ErickFP lo tratan como fuente de verdad -- edita
> con cuidado y documenta el cambio con un ADR.
