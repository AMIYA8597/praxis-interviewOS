# scripts/dev.ps1
Write-Host "Starting PRAXIS Local Development Stack..." -ForegroundColor Cyan

# Ensure we are in the root directory
$rootPath = $PSScriptRoot | Split-Path -Parent
Set-Location $rootPath

# We use Start-Process to multiplex terminal windows natively on Windows
Write-Host "Starting Backend (FastAPI)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit -Command `"cd $rootPath; .\.venv\Scripts\Activate.ps1; uvicorn backend.app.main:app --reload --port 8000`""

Write-Host "Starting Realtime Agent (WebSocket)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit -Command `"cd $rootPath; .\.venv\Scripts\Activate.ps1; uvicorn realtime-agent.app.main:app --reload --port 8001`""

Write-Host "Starting Frontend Web (Next.js)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit -Command `"cd $rootPath; pnpm --filter web dev`""

Write-Host "Starting Desktop Client (Electron)..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit -Command `"cd $rootPath; pnpm --filter desktop dev`""
