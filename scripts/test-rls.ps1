$ErrorActionPreference = 'Stop'

Write-Host "Running RLS Tests..." -ForegroundColor Cyan

# Ensure pytest and psycopg2 are installed
if (-not (Get-Command pytest -ErrorAction SilentlyContinue)) {
    Write-Host "Installing pytest and psycopg2..."
    pip install pytest psycopg2-binary
}

# Run the RLS tests
pytest tests/security/ -v
