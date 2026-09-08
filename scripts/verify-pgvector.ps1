$ErrorActionPreference = 'Stop'

Write-Host "Verifying pgvector extension in local Postgres..." -ForegroundColor Cyan

# The container name might depend on the folder name. Usually foldername-postgres-1
$cid = (docker compose ps -q postgres).Trim()
if ([string]::IsNullOrEmpty($cid)) {
    Write-Host "Postgres container is not running. Did you run infra-up.ps1?" -ForegroundColor Red
    exit 1
}

$sql = "CREATE EXTENSION IF NOT EXISTS vector; SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';"
$result = docker exec $cid psql -U praxis -d praxis -c $sql

Write-Host "`nResult:"
Write-Host $result

if ($result -match "vector") {
    Write-Host "`n[PASS] pgvector extension successfully verified." -ForegroundColor Green
} else {
    Write-Host "`n[FAIL] pgvector extension not found or failed to create." -ForegroundColor Red
    exit 1
}
