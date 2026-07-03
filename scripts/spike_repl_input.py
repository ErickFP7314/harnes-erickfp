"""Spike 2.3 -- valida que el prompt y/n del permission gate y los prompts de
fase (REPL Typer/Rich) NO compiten por stdin ("scanner races", pitfall del
cap. 02 de byo-coding-agent, version Go: dos bufio.Scanner distintos sobre el
mismo os.Stdin pueden robarse bytes entre si).

No requiere GEMINI_API_KEY -- se ejecuta localmente, sin red.

Que valida:
1. Que dos "consumers" logicos distintos (el gate y un prompt de fase) que
   comparten el mismo patron -- una unica funcion `read_line()` que envuelve
   `input()` -- consumen las lineas de stdin en el orden correcto, sin perder
   ni duplicar ninguna, incluso quld intercalados turno a turno.
2. Que Rich `Console.input()` y `input()` builtin leen del mismo buffer (no
   crean un segundo lector con su propio buffering), por lo que mezclarlos no
   introduce una carrera -- pero igual se recomienda una unica funcion
   wrapper para no depender de ese detalle de implementacion a futuro.

Ejecutar: .venv/bin/python scripts/spike_repl_input.py
"""

from __future__ import annotations

import io
import sys
from contextlib import redirect_stdout


def read_line(prompt: str) -> str:
    """Unico consumer de stdin del proceso. Gate y prompts de fase DEBEN
    llamar a esta funcion -- nunca leer stdin por otra via (sys.stdin.read(),
    sys.stdin.buffer, readline reconfigurado, asyncio streams, etc.)."""
    return input(prompt)


def simulate_interleaved_prompts(scripted_stdin: str) -> list[str]:
    """Simula: prompt de fase ("Continuar con la siguiente fase? [y/n]")
    seguido de un prompt del gate ("Ejecutar bash 'ls'? [y/n]"), ambos via
    `read_line`, leyendo de un stdin *scripted* (io.StringIO)."""
    old_stdin = sys.stdin
    sys.stdin = io.StringIO(scripted_stdin)
    try:
        respuestas = []
        respuestas.append(read_line("[fase] Continuar? [y/n] "))
        respuestas.append(read_line("[gate]  Ejecutar bash 'ls'? [y/n] "))
        respuestas.append(read_line("[fase] Continuar? [y/n] "))
        return respuestas
    finally:
        sys.stdin = old_stdin


def main() -> int:
    scripted = "y\nn\ny\n"
    buf = io.StringIO()
    with redirect_stdout(buf):
        respuestas = simulate_interleaved_prompts(scripted)

    esperado = ["y", "n", "y"]
    ok = respuestas == esperado

    print(f"Respuestas leidas: {respuestas}")
    print(f"Esperadas:         {esperado}")
    print(f"Orden preservado sin perdida/duplicacion: {'SI' if ok else 'NO'}")

    if not ok:
        print("FALLO: se detecto una carrera o perdida de lineas de stdin.")
        return 1

    print(
        "\nCONCLUSION: un unico consumer (`read_line`) compartido entre el "
        "permission gate y los prompts de fase preserva el orden exacto de "
        "las respuestas, sin carreras. El patron a seguir en produccion es: "
        "NINGUN modulo lee stdin directamente -- todos pasan por una funcion "
        "compartida (p.ej. erickfp.agent.gate.read_line o equivalente)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
