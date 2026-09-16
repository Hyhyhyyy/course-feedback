$ErrorActionPreference='Stop'
$projectRoot=Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
Push-Location -LiteralPath $projectRoot
try {
    docker info --format '{{.ServerVersion}}'
    if($LASTEXITCODE -ne 0){throw 'Docker engine unavailable. Repair Docker Desktop before starting this pilot.'}
    & .venv/Scripts/python.exe integrations/mediacms/prepare.py
    if($LASTEXITCODE -ne 0){throw 'Pilot preparation failed'}
    docker compose -f outputs/mediacms-pilot/compose.yaml config --quiet
    if($LASTEXITCODE -ne 0){throw 'Compose validation failed'}
    docker compose -f outputs/mediacms-pilot/compose.yaml up -d
    if($LASTEXITCODE -ne 0){throw 'Container startup failed'}
    Write-Output 'Containers requested. Verify health and upload at http://127.0.0.1:8770/ before declaring success.'
} finally {Pop-Location}
