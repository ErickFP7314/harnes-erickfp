# Harnes-ErickFP — Instrucciones del proyecto

## Memoria contextual (OBLIGATORIO)

Para mejorar la memoria contextual usa SIEMPRE el grafo de conocimiento del proyecto antes de explorar a mano:

1. **CodeGraph MCP** (`codegraph_*`): toda pregunta estructural sobre el código (dónde está X, quién llama a Y, qué rompe Z) se responde con `codegraph_context` / `codegraph_search` / `codegraph_explore` — NO con bucles de grep+read. El índice vive en `.codegraph/` y ya está inicializado.
2. **Engram** (`mem_search` / `mem_context` / `mem_get_observation`): al iniciar sesión o retomar un tema, busca primero el contexto persistido (decisiones, ADRs, ciclos SDD previos). Guarda proactivamente con `mem_save` toda decisión, bugfix o descubrimiento.

## Convenciones del producto

- Python >=3.10, CLI con Typer. Capa LLM: interfaz `Provider` propia (adapter LiteLLM); prohibido importar SDKs nativos fuera del adapter.
- Toda decisión técnica traza a un axioma vía ADR markdown (frontmatter: id, parents, estado, trade-off). El agente jamás edita `.ErickFP/core/`.
- Strict TDD: RED → GREEN. Gate de calidad: `pytest -q` + `ruff check .` + `mypy src/erickfp` + `lint-imports` en verde.
- Paquetes SOLO en el venv del proyecto.
- Tema visual: cyan `#00FFFF` (primario) + verde `#00FF00` (acento) sobre `#222222`.

## Subproyectos

- `WebPage/`: landing estática de presentación del producto (ciclo SDD `landing-webpage`). Artefactos en `openspec/changes/landing-webpage/` y engram (`sdd/landing-webpage/*`).
