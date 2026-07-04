# Guía de uso de ErickFP — para usuarios generales

Esta guía te lleva de cero a tu primera sesión completa con ErickFP, sin asumir experiencia previa con agentes de IA. Para detalles de arquitectura y contribución, ve al [README](../README.md).

## ¿Qué es ErickFP, en una frase?

Un asistente de IA que vive en tu terminal, puede leer/escribir archivos y ejecutar comandos **solo con tu permiso**, y que trabaja siguiendo el método de Descartes: primero duda, luego divide, luego construye, y al final revisa.

## 1. Lo que necesitas

1. **Python 3.10 o superior** — verifica con `python3 --version`.
2. **Una API key gratuita de Google Gemini** — entra a [aistudio.google.com/apikey](https://aistudio.google.com/apikey) con tu cuenta de Google y crea una. No pide tarjeta.

> ⚠️ **Tu API key es como una contraseña.** No la pegues en chats, capturas de pantalla ni documentos compartidos — Google detecta keys expuestas y las desactiva automáticamente.

## 2. Instalación (una sola vez)

```bash
git clone git@github.com:ErickFP7314/harnes-erickfp.git
cd harnes-erickfp

python3 -m venv .venv
source .venv/bin/activate      # en cada nueva terminal donde uses erickfp

pip install -e ".[dev]"
erickfp --help                  # si ves la ayuda, todo está bien
```

Guarda tu API key (edita el archivo con tu editor, reemplazando el valor):

```bash
printf 'GEMINI_API_KEY=TU_KEY_AQUI\n' > .env && chmod 600 .env
```

## 3. Tu primer proyecto: `erickfp init`

Ve al directorio del proyecto donde quieras trabajar y ejecuta:

```bash
erickfp init
```

Esto crea la carpeta `.ErickFP/` con:

| Qué | Para qué sirve |
|---|---|
| `core/Claude` | **Los axiomas de tu proyecto**: qué priorizas (legibilidad, seguridad…) y qué sacrificas. La IA los lee antes de cada acción. |
| `core/agents/planner.md`, `coder.md`, `reviewer.md` | Los tres "roles" que la IA adopta según la fase |
| `adr/` | El grafo de decisiones de arquitectura (archivos markdown enlazados) |
| `memory/` | La memoria persistente (SQLite) — la IA recuerda entre sesiones |
| `hooks/` | Punto de extensión para restricciones propias |

**Paso recomendado**: abre `.ErickFP/core/Claude` y escribe tus verdaderas prioridades. Ese archivo gobierna todo lo que la IA haga. Solo tú puedes editarlo — la IA tiene *prohibido* tocarlo (un hook la bloquea aunque tú aprobaras la operación por error).

Si vuelves a correr `init`, no perderás nada: los archivos sagrados solo se sobrescriben si tú lo confirmas explícitamente.

## 4. Conversar: `erickfp chat`

```bash
erickfp chat
```

Ejemplo de sesión:

```
ErickFP chat -- Ctrl+D o 'salir' para terminar.
tu> ¿qué archivos python hay en este proyecto?
[tool] bash {"command": "find . -name '*.py'"}   ¿aprobar? [y/n] y
erickfp> Encontré estos archivos: ...
tu> salir
```

Reglas del juego:

- Cuando la IA quiera ejecutar algo (un comando, leer o escribir un archivo), **te preguntará** `¿aprobar? [y/n]`.
- **Solo la letra `y` aprueba.** Enter vacío, `n`, o cualquier otra cosa = denegado. Es a propósito: el default seguro es "no".
- Si deniegas, no pasa nada malo: la IA recibe "el usuario denegó esto" y buscará otro camino o te preguntará qué prefieres.
- Para salir: escribe `salir`, `exit`, `quit`, o presiona `Ctrl+D`.

## 5. Crear software con el Ciclo Cogito

Para tareas serias, no uses el chat libre — usa el ciclo por fases. Cada fase produce un documento en `.ErickFP/cogito/<slug>/` que alimenta a la siguiente.

### Fase 1 — `duda` (Evidencia)

```bash
erickfp duda "un script que respalde mis fotos a un disco externo"
```

- Si tu objetivo es **claro**, genera `duda.md` con la especificación validada y te muestra el **slug** (el identificador del objetivo, ej. `un-script-que-respalde-mis-fotos-a-un-disco-externo`).
- Si es **ambiguo**, la IA se niega a avanzar y te hace preguntas. Responde afinando tu objetivo y vuelve a intentar. Esto es una función, no un error: el método cartesiano no construye sobre dudas.

### Fase 2 — `divide` (Análisis)

```bash
erickfp divide <slug>
```

El rol **Planner** descompone el objetivo en las partes más pequeñas posibles → `divide.md`.

### Fase 3 — `ordena` (Síntesis)

```bash
erickfp ordena <slug>
```

El rol **Coder** construye de lo simple a lo complejo siguiendo el plan. Aquí los hooks son más estrictos: la síntesis debe ser trazable al grafo ADR.

### Fase 4 — `enumera` (Revisión)

```bash
erickfp enumera <slug>
```

El rol **Reviewer** repasa todo lo producido → `enumera.md`.

### Reglas del ciclo

- **El orden es obligatorio.** Si corres `ordena` sin haber pasado por `divide`, obtendrás un mensaje claro de qué falta (sin errores crípticos).
- Puedes tener **varios objetivos en paralelo** — cada uno vive en su propia carpeta por slug.
- Los artefactos son markdown normal: léelos, edítalos, versiónalos en git.

## 6. Solución de problemas

| Síntoma | Causa probable | Solución |
|---|---|---|
| `No se encontró .ErickFP. Corre 'erickfp init' primero.` | Estás en un directorio sin inicializar | `erickfp init` |
| Error `403 ... API key` | Key inválida, o Google la revocó por exposición | Genera una nueva en AI Studio y actualiza `.env` |
| Error `500 INTERNAL` ocasional | Inestabilidad temporal del proveedor (Gemma 4 es reciente) | El harness reintenta 1 vez solo; si persiste, espera ~15s y reintenta el comando |
| Respuestas lentas (5–15s) | Es la latencia normal del modelo default en free tier | Paciencia, o configura un modelo más rápido (`gemini/gemini-3.5-flash`) |
| `command not found: erickfp` | El venv no está activado | `source .venv/bin/activate` |
| La fase X dice que falta un artefacto | Saltaste una fase del ciclo | Corre la fase anterior primero |

## 7. Preguntas frecuentes

**¿ErickFP puede dañar mi sistema?**
Toda acción con efectos (comandos, escrituras) pasa por tu aprobación explícita. Además, la raíz `.ErickFP/core/` está protegida contra escritura del agente a nivel de hook. Dicho eso: lee lo que apruebas — el gate es tu cinturón de seguridad, no un piloto automático.

**¿Cuánto cuesta usarlo?**
Nada: el modelo default corre en el free tier de la API de Gemini (≈1.500 peticiones/día). Si activas facturación en tu proyecto de Google Cloud, el free tier desaparece — no lo hagas salvo que lo necesites.

**¿Puedo usar otro modelo (Claude, GPT, uno local)?**
La arquitectura está lista para eso (capa de proveedor agnóstica vía LiteLLM), configurable hoy por código. Un comando `--model` está en el roadmap.

**¿Dónde queda lo que la IA "recuerda"?**
En `.ErickFP/memory/` (una base SQLite local). Nada sale de tu máquina salvo lo que el modelo necesita para responder (tus mensajes y los resultados de herramientas que apruebes).
