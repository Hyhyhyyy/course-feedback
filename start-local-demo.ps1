$ErrorActionPreference = 'Stop'
$projectRoot = $PSScriptRoot
Set-Location -LiteralPath $projectRoot
$ready = $false
try { $ready = (Invoke-RestMethod http://127.0.0.1:8081/health -TimeoutSec 2).status -eq 'ok' } catch {}
if (-not $ready) {
    Start-Process -FilePath (Join-Path $projectRoot 'data/runtime/llama/llama-server.exe') -WorkingDirectory $projectRoot -WindowStyle Hidden -ArgumentList @('-m','data/models/qwen35-4b/model.gguf','--mmproj','data/models/qwen35-4b/mmproj.gguf','--host','127.0.0.1','--port','8081','--alias','qwen35-4b','-c','16384','-ngl','0','--parallel','1','--jinja','--reasoning-budget','0','--no-webui','-t','8','-tb','8') -RedirectStandardOutput (Join-Path $projectRoot 'outputs/model-start.out.log') -RedirectStandardError (Join-Path $projectRoot 'outputs/model-start.err.log') | Out-Null
}
$webReady = $false
try { $null = Invoke-RestMethod http://127.0.0.1:8766/api/model/status -TimeoutSec 2; $webReady = $true } catch {}
if (-not $webReady) {
    Start-Process -FilePath (Join-Path $projectRoot '.venv/Scripts/python.exe') -WorkingDirectory $projectRoot -WindowStyle Hidden -ArgumentList @('src/data_server.py','--port','8766') -RedirectStandardOutput (Join-Path $projectRoot 'outputs/workbench-start.out.log') -RedirectStandardError (Join-Path $projectRoot 'outputs/workbench-start.err.log') | Out-Null
}
Write-Output 'Local services starting. Open http://127.0.0.1:8766 and wait until the model status is connected.'
