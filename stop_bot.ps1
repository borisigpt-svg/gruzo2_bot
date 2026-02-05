$ErrorActionPreference = 'SilentlyContinue'

$botDir  = 'C:\GRUZO2\gruzo2_bot'
$launch  = Join-Path $botDir 'launcher.log'
$stopReq = Join-Path $botDir 'stop.request'

$tcpHost = '127.0.0.1'
$tcpPort = 17602

function Write-LauncherLog([string]$msg) {
  try {
    if (!(Test-Path $launch)) { New-Item -ItemType File -Path $launch -Force | Out-Null }
    $ts = Get-Date -Format 'dd.MM.yyyy HH:mm:ss'
    Add-Content -Path $launch -Encoding UTF8 -Value ("[{0}] {1}" -f $ts, $msg)
  } catch {}
}

function Try-TcpStop([int]$timeoutMs) {
  $client = $null
  $stream = $null
  try {
    $client = New-Object System.Net.Sockets.TcpClient

    # connect timeout
    $iar = $client.BeginConnect($tcpHost, $tcpPort, $null, $null)
    if (-not $iar.AsyncWaitHandle.WaitOne($timeoutMs, $false)) {
      try { $client.Close() } catch {}
      return $false
    }
    $client.EndConnect($iar)

    $stream = $client.GetStream()
    $stream.ReadTimeout  = $timeoutMs
    $stream.WriteTimeout = $timeoutMs

    # send STOP + read ACK
    $bytes = [System.Text.Encoding]::ASCII.GetBytes("STOP`n")
    $stream.Write($bytes, 0, $bytes.Length)
    $stream.Flush()

    $buf = New-Object byte[] 32
    $n = $stream.Read($buf, 0, $buf.Length)
    if ($n -le 0) { return $false }

    $ack = ([System.Text.Encoding]::ASCII.GetString($buf, 0, $n)).Trim()
    return ($ack -match '^OK')
  } catch {
    return $false
  } finally {
    try { if ($stream) { $stream.Dispose() } } catch {}
    try { if ($client) { $client.Close() } } catch {}
  }
}

# --- 2 TCP attempts (mil-spec) ---
$timeout = 300

Write-LauncherLog "TCP_STOP try=1 (timeout=${timeout}ms)"
if (Try-TcpStop $timeout) {
  Write-LauncherLog "ACK=OK (tcp, try=1)"
  exit 0
}
Write-LauncherLog "TCP_STOP no-ack (try=1) -> retry"
Start-Sleep -Milliseconds 80

Write-LauncherLog "TCP_STOP try=2 (timeout=${timeout}ms)"
if (Try-TcpStop $timeout) {
  Write-LauncherLog "ACK=OK (tcp, try=2)"
  exit 0
}
Write-LauncherLog "TCP_STOP no-ack (try=2) -> fallback file-command"

# --- fallback: file-command (must-have under autostart) ---
try {
  $ts = Get-Date -Format 'dd.MM.yyyy HH:mm:ss'
  Set-Content -Path $stopReq -Encoding UTF8 -Value $ts -Force
} catch {}

Write-LauncherLog "SOFT_STOP requested (file-command)"
exit 0
