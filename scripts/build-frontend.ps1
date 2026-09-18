param(
  [string]$Target = "both"  # "desktop", "web", or "both"
)

if ($Target -eq "desktop" -or $Target -eq "both") {
  pnpm --filter desktop run build
}
if ($Target -eq "web" -or $Target -eq "both") {
  pnpm --filter web run build
}

Write-Host "✓ Frontend build complete" -ForegroundColor Green
