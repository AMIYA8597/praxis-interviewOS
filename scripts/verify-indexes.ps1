$ErrorActionPreference = 'Stop'

Write-Host "Verifying Index Usage..." -ForegroundColor Cyan

$cid = (docker compose ps -q postgres).Trim()
if ([string]::IsNullOrEmpty($cid)) {
    Write-Host "Postgres container is not running." -ForegroundColor Red
    exit 1
}

cat scripts\verify-indexes.sql | docker exec -i $cid psql -U praxis -d praxis

Write-Host "`nPlease copy the EXPLAIN ANALYZE outputs above and paste them into docs/DATABASE.md under the Verification placeholders." -ForegroundColor Yellow
