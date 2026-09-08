$ErrorActionPreference = 'Stop'

Write-Host "Applying migration to local Postgres..." -ForegroundColor Cyan

$cid = (docker compose ps -q postgres).Trim()
if ([string]::IsNullOrEmpty($cid)) {
    Write-Host "Postgres container is not running. Did you start Docker and run infra-up.ps1?" -ForegroundColor Red
    exit 1
}

# Apply the migration using docker exec psql
cat supabase\migrations\20260907235800_init_core_schema.sql | docker exec -i $cid psql -U praxis -d praxis

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n[PASS] Migration applied successfully!" -ForegroundColor Green
} else {
    Write-Host "`n[FAIL] Migration failed." -ForegroundColor Red
}

Write-Host "`nChecking tables in information_schema..." -ForegroundColor Cyan
docker exec -i $cid psql -U praxis -d praxis -c "\dt"
