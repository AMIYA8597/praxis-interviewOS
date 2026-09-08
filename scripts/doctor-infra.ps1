$ErrorActionPreference = 'SilentlyContinue'

$allPassed = $true

Write-Host "Running Infra Doctor..."
Write-Host "-----------------------"

# 1. Docker Desktop
$dockerInfo = docker info 2>&1
if ($LASTEXITCODE -ne 0 -or $dockerInfo -match "error during connect") {
    Write-Host "[FAIL] Docker Desktop is not installed or not running." -ForegroundColor Red
    Write-Host "       Remediation: Install Docker Desktop from https://www.docker.com/products/docker-desktop/ or start it if already installed." -ForegroundColor Yellow
    $allPassed = $false
} else {
    Write-Host "[PASS] Docker Desktop is running." -ForegroundColor Green
}

# 2. Docker Compose v2
$composeVersion = docker compose version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "[FAIL] Docker Compose v2 is missing." -ForegroundColor Red
    Write-Host "       Remediation: It should come with Docker Desktop. Check your Docker installation." -ForegroundColor Yellow
    $allPassed = $false
} else {
    Write-Host "[PASS] Docker Compose v2 found: $composeVersion" -ForegroundColor Green
}

# 3. Node.js >= 20 and pnpm
$nodeVersion = node -v 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "[FAIL] Node.js is missing." -ForegroundColor Red
    Write-Host "       Remediation: winget install -e --id OpenJS.NodeJS" -ForegroundColor Yellow
    $allPassed = $false
} else {
    $nv = $nodeVersion -replace '^v', ''
    $major = [int]($nv -split '\.')[0]
    if ($major -lt 20) {
         Write-Host "[FAIL] Node.js version is $nodeVersion, but >= 20 is required." -ForegroundColor Red
         Write-Host "       Remediation: winget install -e --id OpenJS.NodeJS" -ForegroundColor Yellow
         $allPassed = $false
    } else {
         Write-Host "[PASS] Node.js >= 20 found: $nodeVersion" -ForegroundColor Green
    }
}

$pnpmVersion = pnpm -v 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "[FAIL] pnpm is missing." -ForegroundColor Red
    Write-Host "       Remediation: npm install -g pnpm" -ForegroundColor Yellow
    $allPassed = $false
} else {
    Write-Host "[PASS] pnpm found: $pnpmVersion" -ForegroundColor Green
}

# 4. Supabase CLI
$supabaseVersion = supabase --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "[FAIL] Supabase CLI is missing." -ForegroundColor Red
    Write-Host "       Remediation: npm install -g supabase" -ForegroundColor Yellow
    $allPassed = $false
} else {
    Write-Host "[PASS] Supabase CLI found: $supabaseVersion" -ForegroundColor Green
}

# 5. psql
$psqlVersion = psql --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "[WARN] psql client is missing." -ForegroundColor Yellow
    Write-Host "       This is not a hard blocker. DBeaver or Supabase Studio web UI are acceptable substitutes." -ForegroundColor Gray
} else {
    Write-Host "[PASS] psql found: $psqlVersion" -ForegroundColor Green
}

# 6. Disk space > 5GB
$driveName = (Get-Location).Drive.Name
$drive = Get-PSDrive -Name $driveName
$freeSpaceGB = [math]::Round($drive.Free / 1GB, 2)
if ($freeSpaceGB -lt 5) {
    Write-Host "[FAIL] Available disk space on ${driveName}: is ${freeSpaceGB}GB, which is under 5GB." -ForegroundColor Red
    Write-Host "       Remediation: Clear some disk space." -ForegroundColor Yellow
    $allPassed = $false
} else {
    Write-Host "[PASS] Disk space OK on ${driveName}: ${freeSpaceGB}GB free." -ForegroundColor Green
}

# 7. Git
$gitVersion = git --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "[FAIL] Git is missing." -ForegroundColor Red
    Write-Host "       Remediation: winget install -e --id Git.Git" -ForegroundColor Yellow
    $allPassed = $false
} else {
    Write-Host "[PASS] Git found: $gitVersion" -ForegroundColor Green
}

Write-Host "-----------------------"
if ($allPassed) {
    Write-Host "All hard blockers passed!" -ForegroundColor Green
    exit 0
} else {
    Write-Host "Some checks failed. Please remediate." -ForegroundColor Red
    exit 1
}
