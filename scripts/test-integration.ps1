$ErrorActionPreference = 'Stop'

Write-Host "Running Integration Tests..." -ForegroundColor Cyan

if (-not (Get-Command pytest -ErrorAction SilentlyContinue)) {
    pip install pytest psycopg2-binary
}

$env:PYTHONPATH = (Get-Item .).FullName
pytest tests/integration/ -v
