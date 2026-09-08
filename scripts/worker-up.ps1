$ErrorActionPreference = 'Stop'

Write-Host "Starting PRAXIS Background Worker..." -ForegroundColor Cyan

# Ensure arq and opentelemetry dependencies are installed
if (-not (Get-Command arq -ErrorAction SilentlyContinue)) {
    Write-Host "Installing arq and opentelemetry dependencies..."
    pip install arq opentelemetry-api opentelemetry-sdk opentelemetry-exporter-otlp
}

$env:PYTHONPATH = (Get-Item .).FullName
# Run arq pointing to the worker_settings module
arq backend.worker_settings.WorkerSettings
