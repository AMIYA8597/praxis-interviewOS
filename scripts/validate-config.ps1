$ErrorActionPreference = 'Stop'

Write-Host "Validating PRAXIS Configuration..." -ForegroundColor Cyan

# Install dependencies if missing
if (-not (Get-Command pydantic-settings -ErrorAction SilentlyContinue) -or -not (python -c "import pydantic_settings" 2>$null)) {
    Write-Host "Installing pydantic-settings and colorama..."
    pip install pydantic-settings colorama
}

$env:PYTHONPATH = (Get-Item .).FullName
python scripts/validate_config.py
