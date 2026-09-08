$ErrorActionPreference = 'Stop'

Write-Host "Running Storage Tests..." -ForegroundColor Cyan

# Ensure pytest and pytest-asyncio are installed
if (-not (Get-Command pytest -ErrorAction SilentlyContinue)) {
    Write-Host "Installing pytest and pytest-asyncio..."
    pip install pytest pytest-asyncio aiofiles supabase
}

# Run local storage test
$env:STORAGE_BACKEND = "local"
$env:PYTHONPATH = (Get-Item .).FullName
pytest tests/infra/test_storage.py -v

Write-Host "`nLocal tests passed! Note: Supabase tests require active cloud credentials." -ForegroundColor Green
