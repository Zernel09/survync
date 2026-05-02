param(
    [string]$ProfileDir = "C:\Users\tanit\AppData\Roaming\ModrinthApp\profiles\NeoForge 1.21.1",
    [string]$SiteDir = "",
    [string]$PackVersion = "1.0.1",
    [string]$BaseUrl = "https://zernel09.github.io/survync/",
    [string[]]$IncludeDirs = @(
        "mods",
        "config",
        "shaderpacks",
        "resourcepacks",
        "kubejs",
        "defaultconfigs",
        "scripts",
        "global_packs"
    )
)

$ErrorActionPreference = "Stop"

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
if ([string]::IsNullOrWhiteSpace($SiteDir)) {
    $SiteDir = Join-Path $RepoRoot "site"
} elseif (-not [System.IO.Path]::IsPathRooted($SiteDir)) {
    $SiteDir = Join-Path $RepoRoot $SiteDir
}

$FilesDir = Join-Path $SiteDir "files"

if (!(Test-Path -LiteralPath $ProfileDir -PathType Container)) {
    throw "Profile directory does not exist: $ProfileDir"
}

Write-Host "--- Generating manifests (v$PackVersion) ---" -ForegroundColor Cyan
& python (Join-Path $RepoRoot "tools\generate_manifest.py") `
    --profile-dir "$ProfileDir" `
    --output-dir "$SiteDir" `
    --pack-version "$PackVersion" `
    --base-download-url "$BaseUrl" `
    --include-dirs $IncludeDirs

if ($LASTEXITCODE -ne 0) {
    throw "Manifest generation failed with exit code $LASTEXITCODE"
}

Write-Host "`n--- Preparing static file directory ---" -ForegroundColor Cyan
New-Item -ItemType Directory -Path $FilesDir -Force | Out-Null

Write-Host "`n--- Copying modpack files ---" -ForegroundColor Cyan
foreach ($dir in $IncludeDirs) {
    $source = Join-Path $ProfileDir $dir
    $dest = Join-Path $FilesDir $dir

    if (Test-Path -LiteralPath $source -PathType Container) {
        Write-Host "Syncing $dir..."
        & robocopy "$source" "$dest" /MIR /NDL /NFL /NJH /NJS /R:3 /W:5
        if ($LASTEXITCODE -ge 8) {
            throw "robocopy failed for $dir with exit code $LASTEXITCODE"
        }
    }
}

Write-Host "Copying top-level config files..."
$RootExtensions = @(".json", ".toml", ".yml", ".yaml", ".cfg", ".properties")
$RootExcludes = @(
    "modrinth.index.json",
    "profile.json",
    "options.txt",
    "optionsof.txt",
    "servers.dat",
    "realms_persistence.json",
    "banned-players.json",
    "ponders_watched.json",
    "usercache.json",
    "usernamecache.json"
)

Get-ChildItem -LiteralPath $FilesDir -File | Where-Object {
    $RootExtensions -contains $_.Extension.ToLowerInvariant()
} | Remove-Item -Force

Get-ChildItem -LiteralPath $ProfileDir -File | Where-Object {
    ($RootExtensions -contains $_.Extension.ToLowerInvariant()) -and
    ($RootExcludes -notcontains $_.Name)
} | ForEach-Object {
    Copy-Item -LiteralPath $_.FullName -Destination $FilesDir -Force
}

Write-Host "`n--- Local sync complete ---" -ForegroundColor Green
Write-Host "Next:" -ForegroundColor Yellow
Write-Host "git add site/"
Write-Host "git commit -m 'Update modpack to v$PackVersion'"
Write-Host "git push"
