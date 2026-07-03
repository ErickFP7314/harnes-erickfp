"""Spike 2.1 [OBLIGATORIO] -- Round-trip de thought signatures de Gemini 3 en
2 turnos con tool calling real via LiteLLM, y comparativa ampliada con
modelos Gemma (instruccion del usuario, 2026-07-03): evaluar si
`gemini/gemma-3-27b-it` (y un Gemma 4 si LiteLLM lo lista bajo el proveedor
`gemini/`) aceptan el parametro `tools` y devuelven tool calls parseables en
2 turnos.

Requiere GEMINI_API_KEY real (se carga desde el .env de la raiz del repo, si
existe). NUNCA se imprime ni loguea el valor de la key.

Salida: imprime en stdout una tabla comparativa y el detalle de cada turno.
Redirigir a un archivo y pegar en docs/spikes/thought-signature.md, o dejar
que un humano/agente con acceso al .env lo ejecute y actualice el doc.

Ejecutar: .venv/bin/python scripts/spike_thought_signature.py
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

# Free tier tipico = 10 RPM. Espaciar cada llamada real >=7s deja margen
# (~8-9 llamadas/min en el peor caso) sin acercarse al limite.
SLEEP_BETWEEN_CALLS_S = 7.0

REPO_ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = REPO_ROOT / ".env"

# Reconstruido a partir del analisis estatico de litellm 1.83.7
# (litellm/litellm_core_utils/prompt_templates/factory.py).
THOUGHT_SIGNATURE_SEPARATOR = "__thought__"

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


def load_dotenv_if_present() -> None:
    """Parser minimo de .env (KEY=VALUE por linea) -- sin dependencia extra
    (YAGNI). No imprime ni loguea valores."""
    if not ENV_PATH.exists():
        return
    for raw_line in ENV_PATH.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def pick_model(candidates: list[str], available: set[str]) -> str | None:
    for c in candidates:
        if c in available:
            return c
    return None


def _call_with_backoff(**kwargs):
    """Una llamada real + hasta 1 reintento con backoff si es rate limit (429).
    Devuelve (respuesta_o_None, latencia_s, error_o_None, fue_429)."""
    import litellm

    for intento in range(2):
        t0 = time.monotonic()
        try:
            resp = litellm.completion(**kwargs)
            return resp, time.monotonic() - t0, None, False
        except Exception as exc:  # noqa: BLE001 -- spike exploratorio
            elapsed = time.monotonic() - t0
            es_429 = "429" in str(exc) or "rate limit" in str(exc).lower() or "RESOURCE_EXHAUSTED" in str(exc)
            if es_429 and intento == 0:
                print("    -> 429/rate-limit detectado, backoff 15s y 1 reintento...")
                time.sleep(15)
                continue
            return None, elapsed, repr(exc), es_429
    return None, 0.0, "no deberia llegar aqui", False


def run_two_turns(model: str) -> dict:
    """Ejecuta 2 turnos de tool-calling contra `model` y reporta si el
    resultado trae una thought signature embebida y si el segundo turno
    (reinyectando el id/tool_call_id tal cual) se completa sin error."""
    result: dict = {
        "model": model, "tools_aceptado": False, "tool_call_recibido": False,
        "thought_signature_detectada": False, "turno_2_ok": False,
        "latencia_turno1_s": None, "latencia_turno2_s": None,
        "rate_limited": False, "error": None,
    }

    messages = [
        {"role": "user", "content": "Que clima hace en Ciudad de Mexico? Usa la tool si hace falta."}
    ]

    resp1, lat1, err1, fue_429_1 = _call_with_backoff(
        model=model, messages=messages, tools=[TOOL_DEF], tool_choice="auto"
    )
    result["latencia_turno1_s"] = round(lat1, 2)
    result["rate_limited"] = result["rate_limited"] or fue_429_1
    if err1 is not None:
        result["error"] = f"turno 1 fallo: {err1}"
        return result

    result["tools_aceptado"] = True
    msg1 = resp1.choices[0].message
    tool_calls = getattr(msg1, "tool_calls", None) or []
    result["tool_call_recibido"] = bool(tool_calls)

    tool_call_id = None
    if tool_calls:
        tool_call_id = tool_calls[0].id
        result["thought_signature_detectada"] = THOUGHT_SIGNATURE_SEPARATOR in (tool_call_id or "")

    # provider_specific_fields.thought_signatures cubre el caso de turnos sin tool_call
    # (bloque de texto/"thinking" con firma propia).
    provider_fields = getattr(msg1, "provider_specific_fields", None) or {}
    if provider_fields.get("thought_signatures"):
        result["thought_signature_detectada"] = True

    if not tool_calls:
        # No hubo tool_use -- no hay turno 2 que reinyectar en este spike.
        return result

    followup_messages = messages + [
        msg1.model_dump() if hasattr(msg1, "model_dump") else msg1,
        {
            "role": "tool",
            "tool_call_id": tool_call_id,
            "content": json.dumps({"clima": "soleado, 24C"}),
        },
    ]

    print(f"    (esperando {SLEEP_BETWEEN_CALLS_S}s antes del turno 2, cuidando el free tier)")
    time.sleep(SLEEP_BETWEEN_CALLS_S)

    resp2, lat2, err2, fue_429_2 = _call_with_backoff(
        model=model, messages=followup_messages, tools=[TOOL_DEF]
    )
    result["latencia_turno2_s"] = round(lat2, 2)
    result["rate_limited"] = result["rate_limited"] or fue_429_2
    if err2 is not None:
        result["error"] = f"turno 2 fallo: {err2}"
    else:
        result["turno_2_ok"] = True

    return result


def main() -> int:
    load_dotenv_if_present()

    if not os.environ.get("GEMINI_API_KEY"):
        print("BLOQUEADO: no se encontro GEMINI_API_KEY (ni en el entorno ni en .env).")
        print(f"Se esperaba el archivo: {ENV_PATH}")
        print("Este spike requiere una API key real de Gemini para producir evidencia empirica.")
        print("Una vez creado el .env con GEMINI_API_KEY=..., re-ejecutar este script.")
        return 2

    import litellm

    available = set(litellm.model_list)

    # Candidatos pedidos explicitamente por el coordinador (2026-07-03), en
    # orden: 3 alias de "Gemini 3 Flash" (el literal "gemini-3-flash" no esta
    # mapeado en litellm 1.83.7, ver hallazgo del analisis estatico) + Gemma 3.
    modelos_a_probar = [
        "gemini/gemini-3-flash-preview",
        "gemini/gemini-flash-latest",
        "gemini/gemini-3.5-flash",
        "gemini/gemma-3-27b-it",
    ]
    no_mapeados = [m for m in modelos_a_probar if m not in available]
    if no_mapeados:
        print(f"AVISO: no mapeados en litellm.model_list (se prueban igual, litellm puede aceptarlos): {no_mapeados}")

    gemma4_candidates = [m for m in available if m.startswith("gemini/") and "gemma-4" in m]
    if not gemma4_candidates:
        print("NOTA: ningun modelo Gemma 4 listado bajo el proveedor 'gemini/' en esta version de litellm -- no evaluable.")

    print(f"Modelos a probar: {modelos_a_probar}\n")

    resultados = []
    for i, model in enumerate(modelos_a_probar):
        print(f"--- Probando {model} ---")
        r = run_two_turns(model)
        resultados.append(r)
        print(json.dumps(r, indent=2, ensure_ascii=False))
        print()
        if i < len(modelos_a_probar) - 1:
            print(f"(esperando {SLEEP_BETWEEN_CALLS_S}s antes del siguiente modelo, cuidando el free tier)\n")
            time.sleep(SLEEP_BETWEEN_CALLS_S)

    print("=== Tabla comparativa ===")
    header = (
        f"{'modelo':35} | {'tools OK':8} | {'tool_call':9} | {'thought_sig':11} | "
        f"{'turno_2_ok':10} | {'lat_t1_s':8} | {'lat_t2_s':8} | {'429?':5}"
    )
    print(header)
    print("-" * len(header))
    for r in resultados:
        print(
            f"{r['model']:35} | {str(r['tools_aceptado']):8} | {str(r['tool_call_recibido']):9} | "
            f"{str(r['thought_signature_detectada']):11} | {str(r['turno_2_ok']):10} | "
            f"{str(r['latencia_turno1_s']):8} | {str(r['latencia_turno2_s']):8} | {str(r['rate_limited']):5}"
        )
        if r["error"]:
            print(f"    error: {r['error']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
