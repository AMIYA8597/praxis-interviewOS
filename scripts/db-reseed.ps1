$ErrorActionPreference = 'Stop'

Write-Host "Resetting and Reseeding Database..." -ForegroundColor Cyan

# 1. Reset Infra
Write-Host "1. Destroying current infrastructure..." -ForegroundColor Yellow
.\scripts\infra-reset.ps1

# 2. Bring Infra Up
Write-Host "2. Bringing infrastructure up..." -ForegroundColor Yellow
.\scripts\infra-up.ps1

# Wait for Postgres to be healthy
Write-Host "Waiting for Postgres to be ready..." -ForegroundColor Yellow
Start-Sleep -Seconds 3

$cid = (docker compose ps -q postgres).Trim()
if ([string]::IsNullOrEmpty($cid)) {
    Write-Host "Postgres container failed to start." -ForegroundColor Red
    exit 1
}

# Wait until psql accepts connections
$maxRetries = 10
$retryCount = 0
while ($retryCount -lt $maxRetries) {
    docker exec -i $cid pg_isready -U praxis | Out-Null
    if ($LASTEXITCODE -eq 0) {
        break
    }
    Start-Sleep -Seconds 2
    $retryCount++
}

if ($retryCount -eq $maxRetries) {
    Write-Host "Timed out waiting for Postgres to be ready." -ForegroundColor Red
    exit 1
}

# 3. Apply Migrations in alphabetical order
Write-Host "3. Applying migrations..." -ForegroundColor Yellow
$migrations = Get-ChildItem "supabase\migrations\*.sql" | Sort-Object Name
foreach ($migration in $migrations) {
    Write-Host "   Applying $($migration.Name)..."
    cat $migration.FullName | docker exec -i $cid psql -U praxis -d praxis
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Failed to apply migration: $($migration.Name)" -ForegroundColor Red
        exit 1
    }
}

# 4. Apply Seed Data
Write-Host "4. Applying seed data..." -ForegroundColor Yellow
cat supabase\seed.sql | docker exec -i $cid psql -U praxis -d praxis
if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to apply seed data." -ForegroundColor Red
    exit 1
}

Write-Host "`nDatabase reset and reseed complete! The synthetic candidate 'Alex Mercer' is ready." -ForegroundColor Green
