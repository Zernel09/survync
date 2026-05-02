# Survync Modpack Sync Script
# Este script automatiza la generación del manifest y la copia de archivos al sitio estático.

$ProfileDir = "C:\Users\tanit\AppData\Roaming\ModrinthApp\profiles\NeoForge 1.21.1"
$SiteDir = ".\site"
$FilesDir = "$SiteDir\files"
$PackVersion = "1.0.1" # Incrementá esto para que el launcher detecte el cambio
$BaseUrl = "https://zernel09.github.io/survync/" # Cambiá esto si tu URL es distinta

Write-Host "--- Generando Manifests (v$PackVersion) ---" -ForegroundColor Cyan
python tools/generate_manifest.py --profile-dir "$ProfileDir" --pack-version "$PackVersion" --base-download-url "$BaseUrl"

if ($LASTEXITCODE -ne 0) {
    Write-Host "Error generando el manifest. Abortando." -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host "`n--- Preparando carpeta de archivos ---" -ForegroundColor Cyan
if (!(Test-Path "$FilesDir")) {
    New-Item -ItemType Directory -Path "$FilesDir" -Force
}

Write-Host "`n--- Copiando archivos del modpack ---" -ForegroundColor Cyan
# Directorios incluidos por defecto en generate_manifest.py
$Dirs = @("mods", "config", "shaderpacks", "resourcepacks", "kubejs", "defaultconfigs", "scripts", "global_packs")

foreach ($dir in $Dirs) {
    if (Test-Path "$ProfileDir\$dir") {
        Write-Host "Sincronizando $dir..."
        # /MIR despeja archivos que ya no existen en el perfil (limpieza de huérfanos en el sitio)
        robocopy "$ProfileDir\$dir" "$FilesDir\$dir" /MIR /NDL /NFL /NJH /NJS /R:3 /W:5
    }
}

# Copiar archivos de configuración en la raíz
Write-Host "Copiando archivos de configuración raíz..."
Get-ChildItem "$ProfileDir" -File | Where-Object { $_.Extension -match "toml|json|yml|yaml|cfg|properties" } | ForEach-Object {
    if ($_.Name -notmatch "modrinth.index.json|profile.json") {
        Copy-Item $_.FullName -Destination "$FilesDir\" -Force
    }
}

Write-Host "`n--- ¡Sincronización local completada! ---" -ForegroundColor Green
Write-Host "Para subir los cambios, ejecutá:" -ForegroundColor Yellow
Write-Host "git add site/"
Write-Host "git commit -m 'Update modpack to v$PackVersion'"
Write-Host "git push"
