"""cogito/artifacts.py -- validacion y persistencia de artefactos markdown
del Ciclo Cogito (Decision 4 del design; spec ciclo-cogito, Requirement
'Fases secuenciales bloqueantes').

Cada fase (excepto `duda`, que no tiene fase previa) exige que el artefacto
de la fase anterior exista y no este vacio antes de ejecutarse -- `require()`
falla limpiamente (excepcion tipada, nunca un crash generico ni un artefacto
parcial de la fase actual) si no es asi (Scenario 'Fase bloqueante sin
artefacto previo').
"""

from __future__ import annotations

from pathlib import Path

_ARTIFACT_FILENAMES = {
    "duda": "duda.md",
    "divide": "divide.md",
    "ordena": "ordena.md",
    "enumera": "enumera.md",
}


class ArtifactMissingError(Exception):
    """El artefacto previo requerido por `phase` no existe o esta vacio."""

    def __init__(self, phase: str, path: Path) -> None:
        self.phase = phase
        self.path = path
        super().__init__(
            f"la fase '{phase}' requiere el artefacto '{path}', pero no existe "
            "o esta vacio -- ejecuta primero la fase anterior del Ciclo Cogito."
        )


def artifact_path(root: Path, slug: str, phase: str) -> Path:
    """Ruta del artefacto markdown de `phase` para el slug dado (Decision 4:
    `.ErickFP/cogito/{slug}/{phase}.md`)."""
    return root / "cogito" / slug / _ARTIFACT_FILENAMES[phase]


def require(path: Path, *, phase: str) -> str:
    """Retorna el contenido de `path` si existe y no esta vacio.

    Lanza `ArtifactMissingError` (nunca crashea con una excepcion generica ni
    produce un artefacto parcial) si el archivo falta o esta vacio tras
    `strip()`.
    """
    if not path.is_file() or not path.read_text().strip():
        raise ArtifactMissingError(phase, path)
    return path.read_text()


def write(path: Path, content: str) -> None:
    """Escribe `content` en `path`, creando directorios padre si hace falta."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
