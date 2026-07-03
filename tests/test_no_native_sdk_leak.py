"""tests/test_no_native_sdk_leak.py -- introspeccion de imports (Decision 2, specs/provider-layer).

Dos invariantes de frontera:
1. Ningun modulo del paquete `erickfp` importa SDKs nativos de LLM
   (`anthropic`, `openai`, `google-genai`) -- ni siquiera el adapter, que solo
   debe hablar con `litellm`.
2. `litellm` en si mismo SOLO puede importarse desde
   `erickfp/provider/litellm_gemini.py` -- ningun otro archivo del paquete
   puede referenciarlo (Decision 2 del design: "ningun simbolo litellm.*
   fuera del adapter").
"""

import ast
from pathlib import Path

NATIVE_SDK_MODULES = {"anthropic", "openai", "google.genai", "google-genai"}
LITELLM_MODULE = "litellm"
ALLOWED_LITELLM_FILE = "provider/litellm_gemini.py"

SRC_ROOT = Path(__file__).resolve().parent.parent / "src" / "erickfp"


def _iter_source_files() -> list[Path]:
    return sorted(SRC_ROOT.rglob("*.py"))


def _imported_top_level_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                modules.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


def test_no_file_imports_native_llm_sdks() -> None:
    offenders: dict[str, set[str]] = {}
    for path in _iter_source_files():
        modules = _imported_top_level_modules(path)
        leaked = {
            m
            for m in modules
            if m.split(".")[0] in {"anthropic", "openai"} or m.startswith("google.genai")
        }
        if leaked:
            offenders[str(path.relative_to(SRC_ROOT))] = leaked

    assert offenders == {}, f"SDK nativo importado fuera del adapter: {offenders}"


def test_only_the_litellm_adapter_imports_litellm() -> None:
    offenders: list[str] = []
    for path in _iter_source_files():
        relative = str(path.relative_to(SRC_ROOT).as_posix())
        modules = _imported_top_level_modules(path)
        imports_litellm = any(
            m == LITELLM_MODULE or m.startswith(f"{LITELLM_MODULE}.") for m in modules
        )
        if imports_litellm and relative != ALLOWED_LITELLM_FILE:
            offenders.append(relative)

    assert offenders == [], f"litellm importado fuera de {ALLOWED_LITELLM_FILE}: {offenders}"


def test_litellm_adapter_file_actually_imports_litellm() -> None:
    adapter_path = SRC_ROOT / ALLOWED_LITELLM_FILE
    assert adapter_path.exists()
    modules = _imported_top_level_modules(adapter_path)
    assert any(m == LITELLM_MODULE for m in modules)
