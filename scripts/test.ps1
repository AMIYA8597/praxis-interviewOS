$ErrorActionPreference = "Stop"

$env:DATABASE_URL="postgresql+asyncpg://localhost:5432/praxis"
$env:REDIS_URL="redis://localhost:6379/0"

Write-Host "Running Backend Tests..." -ForegroundColor Cyan
$env:PYTHONPATH = ".;packages/ai-gateway"
uv run pytest backend/tests/ -v
if ($LASTEXITCODE -ne 0) { throw "Backend tests failed" }

Write-Host "Running AI Gateway Tests..." -ForegroundColor Cyan
$env:PYTHONPATH = ".;packages/ai-gateway"
uv run pytest packages/ai-gateway/tests/ -v
if ($LASTEXITCODE -ne 0) { throw "AI Gateway tests failed" }

Write-Host "Running Realtime Agent Tests..." -ForegroundColor Cyan
$env:PYTHONPATH = ".;packages/ai-gateway;realtime-agent"
uv run pytest realtime-agent/tests/ -v
if ($LASTEXITCODE -ne 0) { throw "Realtime Agent tests failed" }

Write-Host "Running AI Gateway Boundary Check..." -ForegroundColor Cyan
powershell -File scripts/check-gateway-boundary.ps1
if ($LASTEXITCODE -ne 0) { throw "Boundary check failed" }

Write-Host "All CI checks passed!" -ForegroundColor Green
