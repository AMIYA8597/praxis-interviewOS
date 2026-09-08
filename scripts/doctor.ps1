<#
.SYNOPSIS
PRAXIS Dependency Doctor

.DESCRIPTION
Validates that the host Windows 11 machine possesses all required dependencies (Node 20, pnpm, Python 3.12, Docker, FFmpeg, Ollama, GPU) to successfully execute the PRAXIS architectural mandate.
#>

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

Write-Host "Running PRAXIS Toolchain Doctor..." -ForegroundColor Cyan
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

# 2. pnpm
try {
    $pnpmVersion = pnpm --version
    Write-Pass "pnpm version $pnpmVersion found."
} catch {
    Write-Fail "pnpm not found." "Run: corepack enable"
}

# 3. Python >= 3.12 (Check `python` and `py -3.12`)
$pythonFound = $false
try {
    $pyVersionRaw = python --version 2>&1
    if ($pyVersionRaw -match "Python (\d+\.\d+\.\d+)") {
        $pyVersion = [version]$matches[1]
        if ($pyVersion.Major -eq 3 -and $pyVersion.Minor -ge 12) {
            Write-Pass "Python $pyVersion found via 'python'."
            $pythonFound = $true
        }
    }
} catch {}

if (-not $pythonFound) {
    try {
        $pyVersionRaw = py -3.12 --version 2>&1
        if ($pyVersionRaw -match "Python (\d+\.\d+\.\d+)") {
            Write-Pass "Python $([version]$matches[1]) found via 'py -3.12'."
            $pythonFound = $true
        }
    } catch {}
}

if (-not $pythonFound) {
    Write-Fail "Python >= 3.12 not found." "Download Python 3.12+ from https://www.python.org/downloads/windows/"
}

# Check for 'uv' (Recommended)
try {
    $uvVersion = uv --version
    Write-Pass "uv package manager found: $uvVersion"
} catch {
    Write-Host "[WARN] uv package manager not found. It is highly recommended for faster Python dependency resolution on Windows." -ForegroundColor Yellow
    Write-Host "       Remediation: pip install uv" -ForegroundColor Yellow
}

# 4. Git
try {
    $gitVersion = git --version
    Write-Pass "$gitVersion found."
} catch {
    Write-Fail "Git not found." "winget install Git.Git"
}

# 5. Docker Desktop
try {
    $dockerInfo = docker info 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Pass "Docker Desktop is installed and running."
    } else {
        Write-Fail "Docker is installed but the daemon is not running." "Launch Docker Desktop from the Start Menu."
    }
} catch {
    Write-Fail "Docker not found." "winget install Docker.DockerDesktop"
}

# 6. FFmpeg
try {
    $ffmpegInfo = ffmpeg -version 2>&1
    $firstLine = ($ffmpegInfo -split '\r?\n')[0]
    Write-Pass "$firstLine found."
} catch {
    Write-Fail "FFmpeg not found in PATH." "winget install ffmpeg"
}

# 7. Ollama
try {
    $ollamaVersion = ollama --version 2>&1
    Write-Pass "$ollamaVersion found."
} catch {
    Write-Fail "Ollama not found." "winget install Ollama.Ollama (Note: You must run 'ollama pull qwen2.5:3b' per model later in Phase 4)"
}

# 8. Available RAM & GPU
try {
    $os = Get-CimInstance Win32_OperatingSystem
    $ramGB = [math]::Round($os.TotalVisibleMemorySize / 1MB, 2)
    Write-Pass "Total RAM: ${ramGB} GB"
} catch {
    Write-Host "[WARN] Could not determine RAM." -ForegroundColor Yellow
}

try {
    $nvidiaSmi = nvidia-smi 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Pass "NVIDIA GPU found. Local models will run natively."
    } else {
        Write-Host "[INFO] nvidia-smi failed. Proceeding under CPU-only fallback assumption." -ForegroundColor Yellow
    }
} catch {
    Write-Host "[INFO] nvidia-smi not found. Proceeding under CPU-only fallback assumption." -ForegroundColor Yellow
}

Write-Host "-----------------------------------"
if ($global:HasFailures) {
    Write-Host "Doctor failed. Resolve the [FAIL] items before proceeding." -ForegroundColor Red
    exit 1
} else {
    Write-Host "All critical dependencies are met. Proceed to Phase 1." -ForegroundColor Green
}
