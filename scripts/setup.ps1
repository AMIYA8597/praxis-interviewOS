# scripts/setup.ps1
Write-Host "Setting up PRAXIS Environment for Windows 11..." -ForegroundColor Cyan

# 1. Check Python
$pyVersion = py -3.12 --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Python 3.12 not found. Please install Python 3.12 and ensure 'py' launcher is on PATH." -ForegroundColor Red
    exit 1
}

# 2. Check Node & Corepack
$nodeVersion = node --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Node.js not found." -ForegroundColor Red
    exit 1
}
corepack enable
pnpm install

# 3. Setup Virtual Environment
Write-Host "Setting up Python Virtual Environment..." -ForegroundColor Yellow
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
pip install -r realtime-agent/requirements.txt

# 4. Check .env
if (-Not (Test-Path ".env")) {
    Copy-Item ".env.example" -Destination ".env"
    Write-Host "Created .env from .env.example. Please populate Supabase and Provider keys before running dev.ps1." -ForegroundColor Magenta
}

Write-Host "Setup Complete. Run .\scripts\dev.ps1 to start the stack." -ForegroundColor Green
