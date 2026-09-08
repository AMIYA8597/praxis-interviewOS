$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$pythonScript = Join-Path $scriptDir "check_gateway_boundary.py"

python $pythonScript
if ($LASTEXITCODE -ne 0) {
    Write-Error "Gateway boundary check failed."
    exit 1
}
exit 0
