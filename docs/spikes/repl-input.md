# Spike 2.3 -- Prompt y/n compartido en REPL (Typer/Rich)

**Estado**: COMPLETADO. No requiere `GEMINI_API_KEY` (no hace llamadas de red).

**Script**: `scripts/spike_repl_input.py` (ejecutado, exit 0).

## Riesgo evaluado

Pitfall del cap. 02 de `byo-coding-agent` (version Go): si el permission gate
y los prompts de fase usan **dos lectores de stdin distintos** (dos
`bufio.Scanner`/`bufio.Reader` propios), cada uno con su propio buffer interno,
pueden robarse bytes entre si -- una linea tecleada para el prompt A es
consumida por el buffer del lector B, o viceversa ("scanner races").

En Python el equivalente seria mezclar, por ejemplo, `input()` en un sitio con
`sys.stdin.readline()` o `sys.stdin.buffer.read()` en otro, o introducir un
lector de stdin en un hilo/`asyncio` distinto al del hilo principal del REPL.

## Que se valido

1. **Codigo fuente de Rich** (`rich.console.Console.input`, instalado en
   `.venv/`): por defecto (sin `password=True` ni `stream=...` explicito)
   delega directamente en el `input()` builtin de Python -- NO crea un
   segundo buffer sobre `sys.stdin`. Cita del propio metodo: si no hay
   `stream`, hace `result = input()`.
2. **Simulacion con stdin scripteado** (`io.StringIO` inyectado en
   `sys.stdin`): dos "consumers" logicos distintos (un prompt de fase y el
   prompt del gate), ambos pasando por una **unica funcion wrapper**
   `read_line(prompt) -> input(prompt)`, leyeron 3 lineas intercaladas
   (`"y\nn\ny\n"`) en el orden exacto esperado, sin perdida ni duplicacion.

## Conclusion / patron validado

Python (CPython) no sufre el pitfall de Go de forma estructural en un REPL
**sincrono y single-threaded** (nuestro caso: el agent loop y los prompts de
fase corren secuencialmente, nunca en paralelo) siempre que se respete una
regla de diseno:

> **Un unico punto de entrada a stdin.** Tanto el permission gate (Fase 6)
> como cualquier prompt de confirmacion de fase (Fase 7/10) DEBEN llamar a la
> misma funcion (p. ej. `erickfp.agent.gate.read_line()`), que internamente
> usa `input()` (o `Console.input()` sin `stream=`, que es equivalente).
> Ningun modulo debe leer `sys.stdin` por una via alterna (`sys.stdin.read()`,
> `sys.stdin.buffer`, `readline` reconfigurado, hilos o tareas `asyncio` que
> lean stdin concurrentemente).

Esto no requiere codigo de "arbitraje" adicional (no hace falta un lock ni
una cola) -- la sincronia del REPL más una única función de lectura ya
elimina la carrera. La regla se aplicará como convención de código en la
Fase 6 (`src/erickfp/agent/gate.py`) y se documentará ahí con un comentario
que referencia este spike.

## Riesgo residual

Si en el futuro se introduce concurrencia real (p. ej. un timeout de
confirmación con `asyncio` o un hilo separado para heartbeats), esta
conclusión debe revisarse -- el spike asume ejecución estrictamente
secuencial, que es el diseño actual del agent loop (Decisión 3 del
`design.md`: eventos de hooks y turnos del loop son síncronos).
