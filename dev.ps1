# 智能任务规划系统 - 一键启动（分窗口版）
# 后端和前端各开一个独立终端窗口

$rootDir = Split-Path -Parent $MyInvocation.MyCommand.Path

$backendVenv = Join-Path $rootDir "backend\venv\Scripts\python.exe"
$backendPath = Join-Path $rootDir "backend"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  智能任务规划系统 - 启动中..." -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 后端
Write-Host "[1/2] 启动后端 (FastAPI) → 新窗口" -ForegroundColor Green
Start-Process powershell -WindowStyle Normal -ArgumentList @"
cd '$backendPath'; & '$backendVenv' -m uvicorn main:app --reload --host 0.0.0.0 --port 8080; Read-Host '`n后端已停止，按 Enter 关闭'
"@

Start-Sleep -Milliseconds 500

# 前端
Write-Host "[2/2] 启动前端 (Vite) → 新窗口" -ForegroundColor Green
Start-Process powershell -WindowStyle Normal -ArgumentList @"
cd '$rootDir\frontend'; npm run dev; Read-Host '`n前端已停止，按 Enter 关闭'
"@

Write-Host ""
Write-Host "后端窗口: http://localhost:8080" -ForegroundColor Yellow
Write-Host "前端窗口: http://localhost:5173" -ForegroundColor Yellow
Write-Host "API 文档: http://localhost:8080/docs" -ForegroundColor Yellow
Write-Host ""
Write-Host "两个服务已在独立窗口中运行，关闭对应窗口即可停止。" -ForegroundColor Magenta
Write-Host "按 Enter 关闭此启动器..." -ForegroundColor Gray

$null = Read-Host
