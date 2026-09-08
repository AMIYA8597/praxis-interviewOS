$ErrorActionPreference = 'SilentlyContinue'

$allPassed = $true

Write-Host "Running Backend Doctor..."
Write-Host "-----------------------"

# 1. uv is installed
$uvVersion = uv --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "[FAIL] uv is missing." -ForegroundColor Red
    Write-Host "       Remediation: pip install uv" -ForegroundColor Yellow
    $allPassed = $false
} else {
    Write-Host "[PASS] uv found: $uvVersion" -ForegroundColor Green
}

# 2. Uvicorn
$uvicornVersion = uv run uvicorn --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "[FAIL] uvicorn is missing or not working." -ForegroundColor Red
    Write-Host "       Remediation: uv pip install uvicorn" -ForegroundColor Yellow
    $allPassed = $false
} else {
    Write-Host "[PASS] uvicorn found: $uvicornVersion" -ForegroundColor Green
}

# 3. Import tests
$imports = @("fastapi", "arq", "opentelemetry", "numpy")
foreach ($module in $imports) {
    $importOutput = uv run python -c "import $module" 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[FAIL] Python module '$module' failed to import." -ForegroundColor Red
        Write-Host "       Remediation: Ensure your virtual environment is updated." -ForegroundColor Yellow
        $allPassed = $false
    } else {
        Write-Host "[PASS] Python module '$module' imports successfully." -ForegroundColor Green
    }
}

Write-Host "-----------------------"
if ($allPassed) {
    Write-Host "All backend blockers passed!" -ForegroundColor Green
    exit 0
} else {
    Write-Host "Some checks failed. Please remediate." -ForegroundColor Red
    exit 1
}
