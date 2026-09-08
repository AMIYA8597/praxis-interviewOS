$ErrorActionPreference = 'Stop'

Write-Host "WARNING: This will DESTROY all local database and Redis data!" -ForegroundColor Red
$confirmation = Read-Host "Are you sure you want to proceed? Type 'yes' to confirm"

if ($confirmation -ceq 'yes') {
    Write-Host "Bringing down infrastructure and removing volumes..." -ForegroundColor Cyan
    docker compose down -v
    Write-Host "Infrastructure is down and volumes are destroyed." -ForegroundColor Green
} else {
    Write-Host "Aborted. Volumes were not destroyed." -ForegroundColor Yellow
}
