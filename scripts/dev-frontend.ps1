$desktopJob = Start-Job -ScriptBlock { pnpm --filter desktop run dev }
$webJob = Start-Job -ScriptBlock { pnpm --filter web run dev }

Write-Host "✓ Desktop dev server: http://localhost:5173" -ForegroundColor Green
Write-Host "✓ Web dev server: http://localhost:3000" -ForegroundColor Green

Wait-Job $desktopJob, $webJob
