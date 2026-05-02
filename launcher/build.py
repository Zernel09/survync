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
            "--icon", "assets/icon.ico",
            "--add-data", f"assets{data_sep}assets",
            "--paths", "src",
            "src/survync/__main__.py",
        ])
    else:
        cmd.append(str(launcher_dir / "survync.spec"))

    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=str(launcher_dir))
    
    if result.returncode == 0 and args.zip:
        import shutil
        dist_dir = launcher_dir / "dist"
        zip_name = launcher_dir / "dist" / "Survync-Windows"
        
        if (dist_dir / "Survync").is_dir():
            # Zip the folder (onedir)
            shutil.make_archive(str(zip_name), 'zip', str(dist_dir / "Survync"))
            print(f"Created ZIP: {zip_name}.zip")
        elif (dist_dir / "Survync.exe").is_file():
            # Zip the single exe
            import zipfile
            with zipfile.ZipFile(f"{zip_name}.zip", 'w', zipfile.ZIP_DEFLATED) as z:
                z.write(dist_dir / "Survync.exe", "Survync.exe")
            print(f"Created ZIP: {zip_name}.zip")

    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
