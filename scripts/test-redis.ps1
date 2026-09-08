$ErrorActionPreference = 'Stop'

Write-Host "Running Redis Infra Tests..." -ForegroundColor Cyan

# Ensure dependencies are installed
if (-not (Get-Command pytest -ErrorAction SilentlyContinue) -or -not (python -c "import redis" 2>$null)) {
    Write-Host "Installing testing dependencies (pytest, pytest-asyncio, redis)..."
    pip install pytest pytest-asyncio redis
}

$env:PYTHONPATH = (Get-Item .).FullName
pytest tests/infra/test_redis.py -v

Write-Host "`nRedis tests passed!" -ForegroundColor Green
