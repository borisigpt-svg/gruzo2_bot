$ErrorActionPreference = 'Stop'

$botDir   = 'C:\GRUZO2\gruzo2_bot'
$pyw      = Join-Path $botDir '.venv\Scripts\pythonw.exe'
$main     = Join-Path $botDir 'main.py'
$launch   = Join-Path $botDir 'launcher.log'
$mutexName = 'Local\GRUZO2_BOT_LOCK'

# log file must exist
if (!(Test-Path $launch)) { New-Item -ItemType File -Path $launch -Force | Out-Null }

$created = $false
$m = New-Object System.Threading.Mutex($false, $mutexName, [ref]$created)

try {
    if (-not $m.WaitOne(0)) {
        Add-Content -Path $launch -Encoding UTF8 -Value ("[{0}] Already running. Exit." -f (Get-Date -Format 'dd.MM.yyyy HH:mm:ss'))
        exit 0
    }

    Add-Content -Path $launch -Encoding UTF8 -Value ("[{0}] START" -f (Get-Date -Format 'dd.MM.yyyy HH:mm:ss'))

    if (!(Test-Path $pyw)) { throw "pythonw.exe not found: $pyw" }
    if (!(Test-Path $main)) { throw "main.py not found: $main" }

    $p = Start-Process -FilePath $pyw -ArgumentList @($main) -WorkingDirectory $botDir -PassThru
    $p.WaitForExit()
    $code = $p.ExitCode

    Add-Content -Path $launch -Encoding UTF8 -Value ("[{0}] STOP (code={1})" -f (Get-Date -Format 'dd.MM.yyyy HH:mm:ss'), $code)
    exit $code
}
catch {
    Add-Content -Path $launch -Encoding UTF8 -Value ("[{0}] LAUNCHER ERROR: {1}" -f (Get-Date -Format 'dd.MM.yyyy HH:mm:ss'), $_.Exception.Message)
    exit 1
}
finally {
    try { $m.ReleaseMutex() | Out-Null } catch {}
    $m.Dispose()
}
