"""Launch logic for starting the Minecraft modpack via Modrinth."""

from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


def find_modrinth_app() -> Path | None:
    """Locate the Modrinth App executable on Windows.

    Returns the path to the executable, or None if not found.
    """
    candidates: list[Path] = []

    if os.name == "nt":
        local = os.environ.get("LOCALAPPDATA", "")
        if local:
            candidates.append(Path(local) / "Programs" / "modrinth-app" / "Modrinth App.exe")
            candidates.append(
                Path(local) / "Programs" / "ModrinthApp" / "Modrinth App.exe"
            )

        appdata = os.environ.get("APPDATA", "")
        if appdata:
            candidates.append(
                Path(appdata) / "com.modrinth.theseus" / "Modrinth App.exe"
            )

        # Check common install paths
        program_files = os.environ.get("PROGRAMFILES", "C:\\Program Files")
        candidates.append(Path(program_files) / "Modrinth App" / "Modrinth App.exe")

        # Check PATH
        for dir_str in os.environ.get("PATH", "").split(os.pathsep):
            p = Path(dir_str) / "Modrinth App.exe"
            if p.is_file():
                return p
    else:
        # Linux / dev
        for name in ["modrinth-app", "ModrinthApp"]:
            for dir_str in os.environ.get("PATH", "").split(os.pathsep):
                p = Path(dir_str) / name
                if p.is_file():
                    return p

    for candidate in candidates:
        if candidate.is_file():
            logger.info("Found Modrinth App at %s", candidate)
            return candidate

    logger.warning("Could not find Modrinth App executable")
    return None


def launch_profile(
    profile_name: str,
    modrinth_app_path: Path | None = None,
) -> bool:
    """Launch a Modrinth profile.

    Strategy:
    1. Try using the Modrinth App's deep link / CLI if available.
    2. Fall back to opening the Modrinth App (user selects profile manually).

    Args:
        profile_name: The Modrinth profile name to launch.
        modrinth_app_path: Override for the Modrinth App executable path.

    Returns:
        True if launch was initiated successfully.
    """
    if modrinth_app_path is None:
        modrinth_app_path = find_modrinth_app()

    # Strategy 1: Try Modrinth deep link (modrinth://profile/<name>)
    if os.name == "nt":
        deep_link = f"modrinth://profile/{profile_name}"
        try:
            logger.info("Attempting deep link launch: %s", deep_link)
            os.startfile(deep_link)  # type: ignore[attr-defined]
            return True
        except OSError as exc:
            logger.warning("Deep link launch failed: %s", exc)

    # Strategy 2: Try CLI launch
    if modrinth_app_path and modrinth_app_path.is_file():
        try:
            logger.info("Launching Modrinth App: %s", modrinth_app_path)
            if os.name == "nt":
                subprocess.Popen(
                    [str(modrinth_app_path)],
                    creationflags=subprocess.DETACHED_PROCESS,  # type: ignore[attr-defined]
                )
            else:
                subprocess.Popen(
                    [str(modrinth_app_path)],
                    start_new_session=True,
                )
            return True
        except OSError as exc:
            logger.error("Failed to launch Modrinth App: %s", exc)

    # Strategy 3: Open Modrinth App via system association
    if os.name == "nt":
        try:
            os.startfile("modrinth://")  # type: ignore[attr-defined]
            logger.info("Opened Modrinth App via protocol handler")
            return True
        except OSError:
            pass

    logger.error(
        "Could not launch Modrinth App. Please open the Modrinth App manually "
        "and select the '%s' profile.",
        profile_name,
    )
    return False
