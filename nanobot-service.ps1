param(
    [Parameter(Position=0)]
    [ValidateSet("start", "stop", "restart", "status")]
    [string]$Action = "start"
)

$LogDir = "$env:USERPROFILE\.nanobot"
$LogFile = "$LogDir\nanobot.log"

function Start-Nanobot {
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "  nanobot gateway Background Starter" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""

    $pythonw = Get-Command pythonw -ErrorAction SilentlyContinue
    if (-not $pythonw) {
        Write-Host "[ERROR] pythonw not found. Please ensure Python is installed." -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }

    if (-not (Test-Path $LogDir)) {
        New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
    }

    Write-Host "[INFO] Starting nanobot gateway..." -ForegroundColor Yellow
    Write-Host "[INFO] Web UI: http://127.0.0.1:8080" -ForegroundColor Yellow
    Write-Host ""

    $env:PYTHONIOENCODING = "utf-8"
    $env:PYTHONUTF8 = "1"

    Start-Process -FilePath "pythonw" `
                  -ArgumentList "-m", "nanobot", "gateway" `
                  -WindowStyle Hidden `
                  -RedirectStandardOutput "$LogDir\stdout.log" `
                  -RedirectStandardError "$LogDir\stderr.log"

    Write-Host "[INFO] Waiting for service to start..." -ForegroundColor Yellow
    Start-Sleep -Seconds 5

    $maxRetries = 10
    $retryCount = 0
    $started = $false

    while ($retryCount -lt $maxRetries) {
        try {
            $response = Invoke-WebRequest -Uri "http://127.0.0.1:8080/api/health" -UseBasicParsing -TimeoutSec 2
            if ($response.StatusCode -eq 200) {
                $started = $true
                break
            }
        } catch {
            Start-Sleep -Seconds 1
            $retryCount++
        }
    }

    if ($started) {
        Write-Host "[SUCCESS] nanobot gateway is running!" -ForegroundColor Green
        Write-Host "[INFO] Open http://127.0.0.1:8080 in your browser" -ForegroundColor Green
    } else {
        Write-Host "[WARNING] Service may not have started correctly." -ForegroundColor Red
        Write-Host "[INFO] Check logs at: $LogDir" -ForegroundColor Yellow
    }

    Write-Host ""
    Read-Host "Press Enter to close"
}

function Stop-Nanobot {
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "  nanobot gateway Stopper" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""

    Write-Host "[INFO] Stopping nanobot gateway..." -ForegroundColor Yellow

    $processes = Get-WmiObject Win32_Process -Filter "Name='pythonw.exe'" -ErrorAction SilentlyContinue
    foreach ($proc in $processes) {
        if ($proc.CommandLine -like "*nanobot*") {
            Write-Host "[INFO] Killing process PID: $($proc.ProcessId)" -ForegroundColor Yellow
            Stop-Process -Id $proc.ProcessId -Force -ErrorAction SilentlyContinue
        }
    }

    Start-Sleep -Seconds 2
    Write-Host "[DONE] nanobot gateway stopped." -ForegroundColor Green
    Write-Host ""
    Read-Host "Press Enter to close"
}

function Get-NanobotStatus {
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "  nanobot gateway Status" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""

    try {
        $response = Invoke-WebRequest -Uri "http://127.0.0.1:8080/api/health" -UseBasicParsing -TimeoutSec 5
        if ($response.StatusCode -eq 200) {
            Write-Host "[RUNNING] nanobot gateway is running" -ForegroundColor Green
            Write-Host "[INFO] Web UI: http://127.0.0.1:8080" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "[STOPPED] nanobot gateway is not running" -ForegroundColor Red
    }

    Write-Host ""
}

switch ($Action) {
    "start"   { Start-Nanobot }
    "stop"    { Stop-Nanobot }
    "restart" { Stop-Nanobot; Start-Sleep -Seconds 2; Start-Nanobot }
    "status"  { Get-NanobotStatus }
}
