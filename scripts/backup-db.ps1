$ErrorActionPreference = 'Stop'

Write-Host "Running Manual Database Backup..." -ForegroundColor Cyan

# Attempt to load from .env
if (Test-Path .env) {
    # Basic .env parsing to get DATABASE_URL if it's set
    $envContent = Get-Content .env
    foreach ($line in $envContent) {
        if ($line -match "^DATABASE_URL=(.*)") {
            $env:DATABASE_URL = $matches[1]
        }
    }
}

if (-not $env:DATABASE_URL) {
    Write-Host "DATABASE_URL is not set in environment or .env file." -ForegroundColor Red
    exit 1
}

# Ensure pg_dump is available
if (-not (Get-Command pg_dump -ErrorAction SilentlyContinue)) {
    Write-Host "pg_dump is not installed or not in PATH. Please install PostgreSQL client tools." -ForegroundColor Red
    exit 1
}

$Timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$BackupFile = "praxis_backup_$Timestamp.sql"

Write-Host "Dumping to $BackupFile..."
# --clean to add drop commands, --if-exists to avoid errors on drop, --no-owner to allow easy restore
pg_dump --clean --if-exists --no-owner --dbname=$env:DATABASE_URL --file=$BackupFile

Write-Host "Backup completed successfully: $BackupFile" -ForegroundColor Green
