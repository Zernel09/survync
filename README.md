# Survync

Windows-first Minecraft modpack updater for small friend groups using local
Modrinth App profiles. Survync checks a static GitHub Pages manifest, compares
local SHA-256 hashes, downloads only missing or changed files, and then tries to
open the Modrinth profile.

## What Works Today

1. Fetches `version.json` from GitHub Pages.
2. If `pack_version` changed, fetches `manifest.json`.
3. Compares local files against remote SHA-256 hashes.
4. Downloads missing or changed files from `site/files/...`.
5. Optionally removes orphaned files from managed directories.
6. Tries to launch the Modrinth profile through `modrinth://profile/<name>`.

If the Modrinth protocol handler cannot launch a specific profile, Survync opens
the Modrinth App and asks the user to start the profile manually. The Modrinth
App does not expose a fully reliable Windows CLI launch path for every install.

## Repository Layout

```text
survync/
  launcher/                 Desktop app (Python + PySide6)
    src/survync/            Launcher source
    tests/                  Unit tests
    build.py                Local build helper
    survync.spec            PyInstaller spec
    config.sample.json      Sample launcher config
  site/                     Static GitHub Pages payload
    index.html              Status page
    version.json            Pack version metadata
    manifest.json           File manifest with hashes
    files/                  Hosted modpack files
  tools/
    generate_manifest.py    Builds version.json and manifest.json
    sync.ps1                Maintainer script: manifest + site/files copy
  .github/workflows/
    build.yml               Lint, test, build Windows exe artifact
    pages.yml               Deploy site/ to gh-pages
```

## Local Development

```powershell
git clone https://github.com/Zernel09/survync.git
cd survync/launcher
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
python -m survync
```

Run checks:

```powershell
cd launcher
ruff check src/ tests/
pytest tests/ -v
```

## Launcher Configuration

Survync stores config at:

- Windows: `%APPDATA%\Survync\config.json`
- Linux/macOS dev: `~/.config/Survync/config.json`

Important settings:

| Setting | Meaning |
| --- | --- |
| `remote_base_url` | GitHub Pages base URL. Default: `https://zernel09.github.io/survync/` |
| `profile_name` | Modrinth profile folder/name used for auto-detect and deep link launch |
| `profile_path` | Full path to the local Modrinth profile |
| `remove_orphans` | Whether to delete files in managed dirs that are not in the manifest |
| `preserve_paths` | Paths never touched by sync, such as saves, logs, screenshots, options |
| `check_updates_on_start` | Whether to check the remote version when the app opens |

On first launch, Survync tries common Modrinth paths, including:

- `%APPDATA%\ModrinthApp\profiles`
- `%LOCALAPPDATA%\ModrinthApp\profiles`
- legacy `com.modrinth.theseus` paths

If auto-detection fails, the app prompts the user to select the profile folder.

## Maintainer Release Flow

For this repo, the easiest release path is:

```powershell
.\tools\sync.ps1 `
  -ProfileDir "C:\Users\tanit\AppData\Roaming\ModrinthApp\profiles\NeoForge 1.21.1" `
  -BaseUrl "https://zernel09.github.io/survync/"

git add site/ tools/ launcher/ .github/ README.md
git commit -m "Update modpack"
git push
```

`sync.ps1` does two jobs:

1. Runs `tools/generate_manifest.py`.
2. Copies the managed profile files into `site/files/` so the launcher can
   actually download every `download_url` in the manifest.

The script accepts:

| Parameter | Default |
| --- | --- |
| `-ProfileDir` | Your local NeoForge profile path |
| `-SiteDir` | `site/` |
| `-PackVersion` | Current timestamp, for example `2026.05.02.1530` |
| `-BaseUrl` | `https://zernel09.github.io/survync/` |
| `-IncludeDirs` | mods, config, shaderpacks, resourcepacks, kubejs, defaultconfigs, scripts, global_packs |

## Manual Manifest Generation

You can still generate only the JSON files:

```powershell
python tools\generate_manifest.py `
  --profile-dir "C:\Users\YOU\AppData\Roaming\ModrinthApp\profiles\YOUR_PROFILE" `
  --base-download-url "https://zernel09.github.io/survync/"
```

By default, the generator scans:

- `mods/`
- `config/`
- `shaderpacks/`
- `resourcepacks/`
- `kubejs/`
- `defaultconfigs/`
- `scripts/`
- `global_packs/`

It excludes local/player state such as saves, logs, screenshots, options,
server lists, user caches, and temp files.

## GitHub Pages

`.github/workflows/pages.yml` deploys `site/` to the `gh-pages` branch whenever
`site/**` changes on `main`.

Set GitHub Pages to serve from:

- Source: Deploy from a branch
- Branch: `gh-pages`
- Folder: `/`

The deployed files should include:

- `version.json`
- `manifest.json`
- `files/...`

## Building the Windows EXE

Locally:

```powershell
cd launcher
pip install -e ".[dev]"
python build.py --clean
```

Output:

```text
launcher/dist/Survync.exe
```

In GitHub Actions, `.github/workflows/build.yml` runs lint, tests, then builds
the Windows executable and uploads an artifact named `Survync-Windows`.

## Friend Setup

1. Install the Modrinth App.
2. Create or import the expected profile.
3. Run `Survync.exe`.
4. Let Survync auto-detect the profile, or select the profile folder when
   prompted.
5. Click Play.

If the Modrinth deep link is registered and supports the profile name, the
profile opens directly. Otherwise Survync opens Modrinth and tells the user to
launch the profile manually.

## Known Limitations

- No binary delta patches; changed files are downloaded in full.
- No launcher self-update yet.
- Modrinth profile launching depends on the local protocol handler.
- GitHub Pages has size limits. For very large packs, move `files/` to Releases,
  R2, S3, or another static host and set `-BaseUrl` accordingly.
- The optional Modrinth API client is present, but automatic mod resolution is
  not wired into the release flow yet.

## Troubleshooting

**Remote URL not configured**

Open Settings and set `Base URL` to `https://zernel09.github.io/survync/`.

**Profile not found**

Select the profile folder manually. Modern Modrinth App profiles are usually in
`%APPDATA%\ModrinthApp\profiles\`.

**Files fail to download**

Make sure `site/files/` was committed and deployed. The manifest only tells the
launcher what to download; the files must exist at those URLs.

**Files not updating**

By default, `sync.ps1` uses the current timestamp as `PackVersion`. The launcher
checks `pack_version` first, then downloads the manifest only when the version
changed. Use Repair to force full validation.

**Hash mismatch**

The hosted file does not match `manifest.json`. Run `sync.ps1` again, commit
`site/`, and wait for the Pages deployment to finish.

## License

MIT
