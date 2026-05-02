#!/usr/bin/env python3
"""Build script for creating the Survync Windows executable.

Usage:
    python build.py          # Build using the .spec file
    python build.py --onedir # Build as a directory instead of single file
    python build.py --zip    # Create a ZIP file of the output
"""

import argparse
import subprocess
import sys
from pathlib import Path


def get_git_hash() -> str:
    """Obtiene el hash corto del commit actual de git."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        pass
    return "unknown"


def patch_version(init_path: Path, commit_hash: str) -> str:
    """Reemplaza _BUILT_COMMIT en __init__.py con el hash actual.

    Devuelve el contenido original para poder restaurarlo luego.
    """
    original = init_path.read_text(encoding="utf-8")
    patched = original.replace(
        '_BUILT_COMMIT = "unknown"',
        f'_BUILT_COMMIT = "{commit_hash}"',
    )
    init_path.write_text(patched, encoding="utf-8")
    return original


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Survync executable")
    parser.add_argument(
        "--onedir",
        action="store_true",
        help="Build as a directory (faster builds, larger output)",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Clean build directories before building",
    )
    parser.add_argument(
        "--zip",
        action="store_true",
        help="Create a ZIP file of the output",
    )
    args = parser.parse_args()

    launcher_dir = Path(__file__).resolve().parent
    init_path = launcher_dir / "src" / "survync" / "__init__.py"

    if args.clean:
        import shutil
        for d in ["build", "dist"]:
            p = launcher_dir / d
            if p.exists():
                shutil.rmtree(p)
                print(f"Cleaned: {p}")

    # inyectar el hash del commit en __init__.py antes de compilar
    commit_hash = get_git_hash()
    print(f"Commit hash: {commit_hash}")
    original_init = patch_version(init_path, commit_hash)

    cmd = [sys.executable, "-m", "PyInstaller"]

    if args.onedir:
        data_sep = ";" if sys.platform.startswith("win") else ":"
        cmd.extend([
            "--name", "Survync",
            "--onedir",
            "--windowed",
            "--icon", "assets/icon.ico",
            "--add-data", f"assets{data_sep}assets",
            "--paths", "src",
            "src/survync/__main__.py",
        ])
    else:
        cmd.append(str(launcher_dir / "survync.spec"))

    print(f"Running: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, cwd=str(launcher_dir))
    finally:
        # restaurar __init__.py al estado original sin importar si falla la build
        init_path.write_text(original_init, encoding="utf-8")
        print("Restored __init__.py")

    if result.returncode == 0 and args.zip:
        import shutil
        dist_dir = launcher_dir / "dist"
        zip_name = launcher_dir / "dist" / "Survync-Windows"

        if (dist_dir / "Survync").is_dir():
            shutil.make_archive(str(zip_name), "zip", str(dist_dir / "Survync"))
            print(f"Created ZIP: {zip_name}.zip")
        elif (dist_dir / "Survync.exe").is_file():
            import zipfile
            with zipfile.ZipFile(f"{zip_name}.zip", "w", zipfile.ZIP_DEFLATED) as z:
                z.write(dist_dir / "Survync.exe", "Survync.exe")
            print(f"Created ZIP: {zip_name}.zip")

    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
