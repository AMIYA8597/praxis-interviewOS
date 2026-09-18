$ErrorActionPreference = 'SilentlyContinue'

Write-Host "Running AI/ML Doctor..."
Write-Host "-----------------------"

$allPassed = $true

# Check RAM
$mem = Get-CimInstance Win32_OperatingSystem
$totalRamGB = [math]::Round($mem.TotalVisibleMemorySize / 1MB, 2)
Write-Host "Detected RAM: ${totalRamGB}GB" -ForegroundColor Cyan

# Check CPU Cores
$cpu = Get-CimInstance Win32_Processor
$cpuCores = 0
foreach ($c in $cpu) { $cpuCores += $c.NumberOfLogicalProcessors }
Write-Host "Detected CPU Threads: $cpuCores" -ForegroundColor Cyan

# Check GPU
$gpuOutput = nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits 2>&1
$hasGpu = $false
$vramGB = 0

if ($LASTEXITCODE -eq 0 -and $gpuOutput) {
    $hasGpu = $true
    $vramMB = [int]$gpuOutput.Trim()
    $vramGB = [math]::Round($vramMB / 1024, 2)
    Write-Host "Detected NVIDIA GPU with ${vramGB}GB VRAM" -ForegroundColor Cyan
} else {
    Write-Host "No NVIDIA GPU detected." -ForegroundColor Cyan
}

Write-Host ""
Write-Host "RECOMMENDATIONS:" -ForegroundColor Yellow

if ($hasGpu) {
    if ($vramGB -ge 16) {
         Write-Host "- GPU detected with ample VRAM (${vramGB}GB)."
         Write-Host "- faster-whisper: Use GPU ('cuda' compute_type='float16')."
         Write-Host "- Ollama fast_classify: qwen2.5:3b."
         Write-Host "- Ollama reasoning: qwen2.5:14b."
    } elseif ($vramGB -ge 8) {
         Write-Host "- GPU detected with moderate VRAM (${vramGB}GB)."
         Write-Host "- faster-whisper: Use GPU ('cuda' compute_type='float16')."
         Write-Host "- Ollama fast_classify: qwen2.5:3b."
         Write-Host "- Ollama reasoning: qwen2.5:7b or lower to avoid OOM."
    } else {
         Write-Host "- GPU detected but limited VRAM (${vramGB}GB)."
         Write-Host "- faster-whisper: Use GPU ('cuda' compute_type='int8') if possible, else CPU."
         Write-Host "- Ollama fast_classify: qwen2.5:1.5b or 3b."
         Write-Host "- Ollama reasoning: qwen2.5:3b."
    }
} else {
    Write-Host "- No GPU detected (CPU-only mode)."
    $threads = [math]::Min($cpuCores, 8)
    Write-Host "- faster-whisper: recommend 'small.en' on CPU with $threads threads."
    Write-Host "- Ollama fast_classify: qwen2.5:3b (needs ~4GB RAM)."
    if ($totalRamGB -ge 16) {
        Write-Host "- Ollama reasoning: qwen2.5:7b (instead of 14b) for faster CPU inference."
    } else {
        Write-Host "- Ollama reasoning: qwen2.5:3b (RAM < 16GB, 14b will be too slow)."
    }
}
Write-Host "-----------------------"
