#!/usr/bin/env python3
"""Build script for creating the Survync Windows executable.

Usage:
    python build.py          # Build using the .spec file
    python build.py --onedir # Build as a directory instead of single file
"""

import argparse
import subprocess
import sys
from pathlib import Path


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
    args = parser.parse_args()

    launcher_dir = Path(__file__).resolve().parent

    if args.clean:
        import shutil

        for d in ["build", "dist"]:
            p = launcher_dir / d
            if p.exists():
                shutil.rmtree(p)
                print(f"Cleaned: {p}")

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
    ]

    if args.onedir:
        data_sep = ";" if sys.platform.startswith("win") else ":"
        cmd.extend([
            "--name", "Survync",
            "--onedir",
            "--windowed",
            "--add-data", f"assets{data_sep}assets",
            "--paths", "src",
            "src/survync/__main__.py",
        ])
    else:
        cmd.append(str(launcher_dir / "survync.spec"))

    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=str(launcher_dir))
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
