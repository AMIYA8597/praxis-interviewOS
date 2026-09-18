$ErrorActionPreference = "Stop"

function Write-Pass ($Message) {
    Write-Host "[PASS] $Message" -ForegroundColor Green
}

function Write-Fail ($Message, $Remediation) {
    Write-Host "[FAIL] $Message" -ForegroundColor Red
    Write-Host "       Remediation: $Remediation" -ForegroundColor Yellow
    $global:HasFailures = $true
}

$global:HasFailures = $false

Write-Host "Running PRAXIS Frontend Doctor..." -ForegroundColor Cyan
Write-Host "-----------------------------------"

# 1. Node.js >= 20
try {
    $nodeVersion = node --version
    $versionNum = [version]($nodeVersion.TrimStart('v'))
    if ($versionNum.Major -ge 20) {
        Write-Pass "Node.js $nodeVersion found."
    } else {
        Write-Fail "Node.js version is $nodeVersion (requires >= 20)." "Download Node.js 20+ from https://nodejs.org/"
    }
} catch {
    Write-Fail "Node.js not found." "Download Node.js 20+ from https://nodejs.org/"
}

# 2. Package manager (pnpm used in this project)
try {
    $pnpmVersion = pnpm --version
    Write-Pass "pnpm version $pnpmVersion found."
} catch {
    Write-Fail "pnpm not found." "Run: corepack enable"
}

Write-Host "-----------------------------------"
if ($global:HasFailures) {
    Write-Host "Frontend Doctor failed. Resolve the [FAIL] items before proceeding." -ForegroundColor Red
    exit 1
} else {
    Write-Host "All frontend dependencies are met. Proceed." -ForegroundColor Green
}
