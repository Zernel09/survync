"""Survync - Minecraft modpack launcher and updater."""

import subprocess
from pathlib import Path

__app_name__ = "Survync"

# intenta obtener el hash corto del commit actual de git
# si no hay git (ej: ejecutable buildeado), usa el hash inyectado en build time
_BUILT_COMMIT = "unknown"  # reemplazado por build.py al compilar


def _get_git_hash() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=2,
            cwd=Path(__file__).resolve().parent,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        pass
    return _BUILT_COMMIT


__version__ = _get_git_hash()
