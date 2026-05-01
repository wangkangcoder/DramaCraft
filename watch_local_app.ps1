param(
    [Parameter(Mandatory = $true)]
    [int]$BackendPid,

    [Parameter(Mandatory = $true)]
    [string]$BrowserProfileDir,

    [Parameter(Mandatory = $true)]
    [string]$BrowserPidFile,

    [Parameter(Mandatory = $true)]
    [string]$BackendPidFile,

    [string]$WatcherPidFile = ''
)

function Test-ManagedBrowserAlive {
    $profilePattern = [regex]::Escape($BrowserProfileDir)
    $processes = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
        ($_.Name -ieq 'msedge.exe' -or $_.Name -ieq 'chrome.exe') -and
        $_.CommandLine -match $profilePattern
    }

    return [bool]$processes
}

function Stop-BackendIfRunning {
    try {
        $backend = Get-Process -Id $BackendPid -ErrorAction SilentlyContinue
        if ($backend) {
            Stop-Process -Id $BackendPid -Force -ErrorAction SilentlyContinue
        }
    } catch {
    }
}

function Cleanup-State {
    Remove-Item -LiteralPath $BrowserPidFile -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $BackendPidFile -Force -ErrorAction SilentlyContinue

    if ($WatcherPidFile) {
        Remove-Item -LiteralPath $WatcherPidFile -Force -ErrorAction SilentlyContinue
    }

    if (Test-Path -LiteralPath $BrowserProfileDir) {
        Remove-Item -LiteralPath $BrowserProfileDir -Recurse -Force -ErrorAction SilentlyContinue
    }
}

$seenManagedWindow = $false
$checks = 0

while ($true) {
    if (Test-ManagedBrowserAlive) {
        $seenManagedWindow = $true
    } elseif ($seenManagedWindow) {
        break
    } elseif ($checks -ge 15) {
        Stop-BackendIfRunning
        Cleanup-State
        exit 0
    }

    Start-Sleep -Seconds 1
    $checks++
}

if (-not $seenManagedWindow) {
    Stop-BackendIfRunning
    Cleanup-State
    exit 0
}

Stop-BackendIfRunning
Cleanup-State
