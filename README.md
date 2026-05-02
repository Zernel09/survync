# Survync

A Windows-first Minecraft modpack launcher and updater designed for small friend groups using Modrinth profiles. Your friends only need to run a `.exe`, click **Play**, and the app handles the rest — checking for updates, syncing only changed files, and launching the pack.

## Architecture

```
survync/
├── launcher/              # Desktop app (Python + PySide6)
│   ├── src/survync/       # Source code
│   │   ├── __main__.py    # Entry point
│   │   ├── config.py      # Configuration management
│   │   ├── hasher.py      # SHA-256 file hashing
│   │   ├── launcher.py    # Modrinth profile launch logic
│   │   ├── models.py      # Data models
│   │   ├── modrinth_api.py# Optional Modrinth REST API client
│   │   ├── network.py     # HTTP client with retries
│   │   ├── profile_detector.py # Auto-detect Modrinth profiles
│   │   ├── sync_engine.py # Core diff + sync engine
│   │   └── ui/            # PySide6 GUI
│   │       ├── main_window.py
│   │       ├── settings_dialog.py
│   │       ├── styles.py
│   │       └── workers.py # Background threads
│   ├── tests/             # Unit tests
│   ├── assets/            # Icons and resources
│   ├── pyproject.toml     # Python project config
│   ├── survync.spec       # PyInstaller build spec
│   ├── build.py           # Build helper script
│   └── config.sample.json # Sample configuration
├── site/                  # GitHub Pages static site
│   ├── index.html         # Status page
│   ├── version.json       # Pack version metadata
│   └── manifest.json      # File manifest with hashes
├── tools/                 # Admin/maintainer scripts
│   └── generate_manifest.py  # Manifest generator
├── .github/workflows/     # CI/CD
│   ├── build.yml          # Lint, test, build .exe
│   └── pages.yml          # Deploy site to gh-pages
└── README.md
```

### How It Works

```
┌─────────────┐     HTTPS      ┌──────────────────┐
│  Survync    │  ──────────►   │  GitHub Pages    │
│  Launcher   │                │  (gh-pages)      │
│  (.exe)     │  ◄──────────   │                  │
│             │   version.json │  version.json    │
│  Compares   │   manifest.json│  manifest.json   │
│  local hash │                │  /files/...      │
│  vs remote  │                └──────────────────┘
│             │
│  Downloads  │     Launches
│  diff only  │  ──────────►   Modrinth App
└─────────────┘                (survival profile)
```

1. **Check**: Fetches `version.json` from your GitHub Pages site
2. **Compare**: If version differs, fetches `manifest.json` and compares SHA-256 hashes of local files
3. **Sync**: Downloads only missing or changed files using atomic writes (temp file → rename)
4. **Launch**: Opens the Modrinth App with the correct profile

## Local Development Setup

### Prerequisites

- Python 3.10+ ([python.org](https://www.python.org/downloads/))
- Git

### Setup

```bash
# Clone the repo
git clone https://github.com/Zernel09/survync.git
cd survync

# Create a virtual environment
python -m venv .venv

# Activate it
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# Install the launcher in dev mode
cd launcher
pip install -e ".[dev]"
```

### Run the Launcher (Dev Mode)

```bash
# From the launcher/ directory
python -m survync
```

### Run Tests

```bash
cd launcher
pytest tests/ -v
```

### Lint

```bash
cd launcher
ruff check src/ tests/
```

## Configuration

The launcher stores its config at:
- **Windows**: `%APPDATA%\Survync\config.json`
- **Linux**: `~/.config/Survync/config.json`

On first launch, the app creates a default config. You can also copy `launcher/config.sample.json` to the config location and edit it.

### Key Settings

| Setting | Description | Default |
|---------|-------------|---------|
| `remote_base_url` | URL to your GitHub Pages site | `""` (must be set) |
| `profile_name` | Modrinth profile folder name | `"survival"` |
| `profile_path` | Full path to the profile (auto-detected on Windows) | `""` |
| `modrinth_project_slug` | Optional: Modrinth project slug for API integration | `null` |
| `modrinth_project_id` | Optional: Modrinth project ID for API integration | `null` |
| `remove_orphans` | Delete local files not in the remote manifest | `false` |
| `preserve_paths` | Paths that are never modified by sync | saves, screenshots, logs, etc. |
| `check_updates_on_start` | Auto-check for updates on launch | `true` |

### Pointing to GitHub Pages

After publishing your site, set `remote_base_url` in the launcher settings to:

```
https://<your-username>.github.io/survync/
```

For this repo, that would be:
```
https://zernel09.github.io/survync/
```

## Generating the Manifest

The manifest generator scans your local Modrinth profile and produces `version.json` and `manifest.json`.

### Basic Usage

```bash
cd tools

# Scan and generate (writes to ../site/)
python generate_manifest.py \
  --profile-dir "C:\Users\YOU\AppData\Roaming\com.modrinth.theseus\profiles\survival" \
  --pack-version "1.0.0" \
  --base-download-url "https://zernel09.github.io/survync/"

# Dry run (shows what would be generated without writing)
python generate_manifest.py \
  --profile-dir "C:\Users\YOU\AppData\Roaming\com.modrinth.theseus\profiles\survival" \
  --dry-run
```

### Options

| Flag | Description |
|------|-------------|
| `--profile-dir` | Path to the local Modrinth profile directory (**required**) |
| `--output-dir` | Where to write JSON files (default: `../site/`) |
| `--pack-name` | Pack display name (default: `survival`) |
| `--pack-version` | Version string (default: `1.0.0`) |
| `--minecraft-version` | Minecraft version (default: `1.20.4`) |
| `--loader-name` | Mod loader (default: `fabric`) |
| `--loader-version` | Loader version (default: `0.15.0`) |
| `--base-download-url` | Base URL for download links |
| `--include-dirs` | Override which directories to scan |
| `--exclude-patterns` | Additional glob patterns to exclude |
| `--dry-run` | Preview output without writing files |

### What Gets Included

By default, the generator scans these directories:
- `mods/`, `config/`, `shaderpacks/`, `resourcepacks/`
- `kubejs/`, `defaultconfigs/`, `scripts/`, `global_packs/`

And excludes:
- `saves/`, `screenshots/`, `logs/`, `crash-reports/`
- `options.txt`, `servers.dat`, temp files, OS files

### Hosting Mod Files

The `download_url` in the manifest points to where the launcher will download each file. You have two options:

1. **Host files alongside the manifest** (simplest): Upload mod files to a `files/` directory on your GitHub Pages site or another static host
2. **Use direct URLs**: If mods are publicly downloadable (e.g., from Modrinth CDN), you can manually edit the manifest to point to those URLs

> **Note**: For large modpacks, consider using GitHub Releases or an external file host instead of the `gh-pages` branch (GitHub Pages has a 1 GB size limit).

## Publishing to GitHub Pages

### Initial Setup

1. Go to your repo's **Settings → Pages**
2. Set Source to **Deploy from a branch**
3. Select the **gh-pages** branch and **/ (root)** folder
4. Save

### Automatic Deployment

The included GitHub Actions workflow (`.github/workflows/pages.yml`) automatically deploys the `site/` directory to the `gh-pages` branch whenever you push changes to `site/` on `main`.

### Manual Deployment

```bash
# After generating new manifests, commit and push to main
git add site/
git commit -m "Update pack manifest to v1.1.0"
git push origin main
# The GitHub Action will deploy to gh-pages automatically
```

Alternatively, deploy manually:

```bash
# Create/update the gh-pages branch
git checkout --orphan gh-pages
git rm -rf .
cp -r site/* .
git add .
git commit -m "Deploy site"
git push origin gh-pages --force
git checkout main
```

## Building the Windows .exe

### Locally

```bash
cd launcher
pip install -e ".[dev]"
python build.py
# Output: dist/Survync.exe
```

### Via GitHub Actions

1. Push to `main` or open a PR
2. The **Build & Test** workflow runs automatically
3. Download the `Survync-Windows` artifact from the workflow run's **Artifacts** section

## How Your Friends Use the Launcher

1. **Download** the `Survync.exe` from GitHub Actions artifacts (or from wherever you share it)
2. **Install the Modrinth App** and create a profile named `survival` (or whatever your pack uses)
3. **Run `Survync.exe`**
4. **First launch**: The app auto-detects the `survival` Modrinth profile. If not found, it prompts to select the profile folder
5. **Click Play**: The app checks for updates, downloads only changed files, then launches the Modrinth App

That's it. No Python installation, no command line, no manual file management.

### For the Pack Maintainer (You)

Your workflow for releasing an update:

1. Update mods/configs in your local `survival` Modrinth profile
2. Run the manifest generator:
   ```bash
   python tools/generate_manifest.py \
     --profile-dir "path/to/survival" \
     --pack-version "1.1.0" \
     --base-download-url "https://zernel09.github.io/survync/"
   ```
3. Upload the new/changed mod files to your file host
4. Commit and push the updated `site/version.json` and `site/manifest.json`
5. Your friends' launchers will pick up the update next time they click Play

## Known Limitations and Future Improvements

### Current Limitations

- **File hosting is manual**: You need to upload mod files to a static host separately. The manifest generator creates download URLs but doesn't upload files
- **No delta/patch downloads**: Files are downloaded in full, not as binary diffs
- **No auto-update for the launcher itself**: Friends need to manually update the `.exe`
- **Modrinth deep link launch**: The `modrinth://profile/` protocol may not be registered on all systems. Falls back to opening the Modrinth App directly
- **Windows-first**: The app is designed for Windows. It works on Linux/macOS for development but profile auto-detection and launch are Windows-optimized

### Future Improvements

- [ ] Automatic file upload to GitHub Releases or R2/S3
- [ ] Launcher self-update mechanism
- [ ] Progress bar for individual file downloads (currently per-file granularity)
- [ ] Modrinth API integration for automatic mod resolution
- [ ] Pack export/import for initial setup
- [ ] Tray icon / minimize to tray
- [ ] Custom app icon

## Troubleshooting

### "Remote URL not configured"
Open Settings and set the `Base URL` to your GitHub Pages URL (e.g., `https://zernel09.github.io/survync/`).

### "Profile not found"
The launcher couldn't auto-detect your Modrinth profile. Open Settings and either:
- Set the correct profile name
- Browse to the profile folder manually (typically `%APPDATA%\com.modrinth.theseus\profiles\survival`)

### "Network error" / "Failed to fetch"
- Check your internet connection
- Verify the GitHub Pages site is live by visiting the URL in a browser
- The server might be temporarily unavailable — try again in a few minutes

### "Hash mismatch" after download
The downloaded file doesn't match the expected hash. This usually means:
- The file on the server was updated without regenerating the manifest
- Network corruption (rare)

Fix: Click **Repair** to re-validate and re-download mismatched files.

### Launcher crashes on startup
Check the log file at `%APPDATA%\Survync\survync.log` for error details.

### Files not updating
- Make sure you committed and pushed the updated `version.json` and `manifest.json`
- Verify the GitHub Pages deployment completed (check the Actions tab)
- The launcher compares versions first — if `pack_version` didn't change, it won't re-check files
- Use **Repair** to force a full re-validation

### Modrinth App doesn't launch
- Ensure the Modrinth App is installed
- Try opening the Modrinth App manually and selecting the profile
- On Windows, the launcher tries the `modrinth://` protocol handler first, then direct executable launch

## License

MIT
