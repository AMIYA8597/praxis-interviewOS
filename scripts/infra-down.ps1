$ErrorActionPreference = 'Stop'

Write-Host "Bringing down infrastructure..." -ForegroundColor Cyan
docker compose down
Write-Host "Infrastructure is down." -ForegroundColor Green
