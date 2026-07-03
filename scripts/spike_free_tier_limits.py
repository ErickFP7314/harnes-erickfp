"""Spike 2.2 -- mide, con llamadas reales, si el free tier (10 RPM tipico de
Gemini API) alcanza para un turno agentico multi-tool (ida-vuelta tipo
duda->tool_use->tool_result->respuesta).

Requiere GEMINI_API_KEY real (se carga desde .env de la raiz, si existe).
NUNCA se imprime ni loguea el valor de la key.

Estrategia: dispara N llamadas secuenciales de `litellm.completion` con
tools, simulando un turno agentico corto (2-3 llamadas por "turno logico"),
mide el tiempo entre llamadas y cuenta cuantas llamadas caben antes de un
error 429 (rate limit) o similar. No implementa backoff -- el objetivo es
medir el limite crudo, no evitarlo.

Ejecutar: .venv/bin/python scripts/spike_free_tier_limits.py
"""

from __future__ import annotations

import os
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = REPO_ROOT / ".env"

TOOL_DEF = {
    "type": "function",
    "function": {
        "name": "get_clima",
        "description": "Devuelve el clima actual de una ciudad.",
        "parameters": {
            "type": "object",
            "properties": {"ciudad": {"type": "string"}},
            "required": ["ciudad"],
        },
    },
}

# N llamadas a intentar; 15 > 10 RPM del free tier tipico para forzar el
# limite dentro de la ventana de un minuto si existe.
N_LLAMADAS = 15
MODELO = "gemini/gemini-3-flash-preview"  # ver docs/spikes/thought-signature.md


def load_dotenv_if_present() -> None:
    if not ENV_PATH.exists():
        return
    for raw_line in ENV_PATH.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def main() -> int:
    load_dotenv_if_present()

    if not os.environ.get("GEMINI_API_KEY"):
        print("BLOQUEADO: no se encontro GEMINI_API_KEY (ni en el entorno ni en .env).")
        print(f"Se esperaba el archivo: {ENV_PATH}")
        print("Este spike requiere una API key real para medir limites reales del free tier.")
        return 2

    import litellm

    messages = [{"role": "user", "content": "Que clima hace en Ciudad de Mexico?"}]

    t0 = time.monotonic()
    exitosas = 0
    for i in range(N_LLAMADAS):
        t_call = time.monotonic()
        try:
            litellm.completion(model=MODELO, messages=messages, tools=[TOOL_DEF])
            exitosas += 1
            estado = "OK"
        except Exception as exc:  # noqa: BLE001 -- spike exploratorio
            estado = f"ERROR: {exc!r}"
        elapsed = time.monotonic() - t_call
        total = time.monotonic() - t0
        print(f"[{i + 1:02}/{N_LLAMADAS}] t={total:6.2f}s (+{elapsed:5.2f}s) -> {estado}")
        if estado != "OK":
            break

    print(f"\nLlamadas exitosas antes de fallo/fin: {exitosas}/{N_LLAMADAS}")
    print(
        "Si `exitosas` < N_LLAMADAS por un error de rate limit (429 o similar), "
        "el free tier NO alcanza para ~15 llamadas en <1 min y se necesita "
        "backoff/cache. Si todas fueron OK, medir cuantas llamadas reales "
        "produce un turno agentico tipico (duda con 1-2 tool calls) y "
        "comparar contra el limite medido aqui."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
