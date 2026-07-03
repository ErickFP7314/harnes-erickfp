# Grafo ADR -- `.ErickFP/adr/`

Cada decision de arquitectura relevante vive aqui como un archivo markdown
`NNN-titulo.md` con frontmatter YAML:

```yaml
---
id: 1
titulo: "Ejemplo de decision raiz"
parents: []              # lista vacia = nodo raiz; debe declarar un axioma de core/Claude
estado: aceptada          # propuesta | aceptada | rechazada | amendment
trade_off: "Describe la concesion que se acepta al tomar esta decision"
---
```

## Validacion de trazabilidad

El hook `adr_traceability` (fase `ordena`) valida que todo ADR objetivo
alcance, por DFS a traves de `parents`, un nodo raiz (`parents: []`) que
declare un axioma de `core/Claude`. Falla (bloquea la fase) si:

- Un id de `parents` no existe.
- Se detecta un ciclo (un id ya visitado reaparece en la pila).
- Algun camino no termina en un nodo raiz.

Crea tus propios ADRs numerandolos secuencialmente a partir de `001`.
