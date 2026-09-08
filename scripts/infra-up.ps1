$ErrorActionPreference = 'SilentlyContinue'

Write-Host "Bringing up infrastructure..." -ForegroundColor Cyan
docker compose up -d
if ($LASTEXITCODE -ne 0) {
    Write-Host "docker compose up failed." -ForegroundColor Red
    exit 1
}

Write-Host "Waiting for services to become healthy (up to 60s)..." -ForegroundColor Cyan

$services = @("postgres", "redis", "jaeger")
$timeoutSeconds = 60
$sw = [System.Diagnostics.Stopwatch]::StartNew()

$allHealthy = $true

foreach ($svc in $services) {
    $isHealthy = $false
    while ($sw.Elapsed.TotalSeconds -lt $timeoutSeconds) {
        $cid = (docker compose ps -q $svc).Trim()
        if (-not [string]::IsNullOrEmpty($cid)) {
            $healthStatus = (docker inspect --format="{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}" $cid).Trim()
            
            if ($healthStatus -eq "healthy" -or ($healthStatus -eq "running" -and $svc -eq "jaeger")) {
                $isHealthy = $true
                break
            }
        }
        Start-Sleep -Seconds 2
    }

    if ($isHealthy) {
        Write-Host "[PASS] $svc is healthy/running." -ForegroundColor Green
    } else {
        Write-Host "[FAIL] $svc failed to become healthy." -ForegroundColor Red
        $allHealthy = $false
        Write-Host "--- Last 20 lines of $svc logs ---" -ForegroundColor Yellow
        docker compose logs --tail=20 $svc
        Write-Host "----------------------------------" -ForegroundColor Yellow
    }
}

if ($allHealthy) {
    Write-Host "`nAll services are up and healthy!" -ForegroundColor Green
    Write-Host "DATABASE_URL: <configured through environment>"
    Write-Host "REDIS_URL:    redis://localhost:6379"
    Write-Host "JAEGER UI:    http://localhost:16686"
} else {
    Write-Host "`nSome services failed to start correctly." -ForegroundColor Red
    exit 1
}
