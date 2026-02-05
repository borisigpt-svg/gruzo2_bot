param(
  [Parameter(Position=0)]
  [ValidateSet("status","start","stop","restart","tail","health","fixjson","backup")]
  [string]$Action = "status",


  [int]$Tail = 200,
  [switch]$Follow,


  [ValidateSet("app","launcher")]
  [string]$Log = "app",


  [switch]$Foreground,

    [switch]$Force,



  [string]$StopTcpHost = "127.0.0.1",
  [int]$StopTcpPort = 17602,
  [int]$StopTimeoutMs = 300
)


$ErrorActionPreference = "Stop"


function Section([string]$t) { Write-Host ""; Write-Host ("==== " + $t + " ====") }
function OK([string]$t)      { Write-Host ("[OK]   " + $t) }
function WARN([string]$t)    { Write-Host ("[WARN] " + $t) }
function FAIL([string]$t)    { Write-Host ("[FAIL] " + $t) }


$BotDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $BotDir


$Main    = Join-Path $BotDir "main.py"
$PyVenv  = Join-Path $BotDir ".venv\Scripts\python.exe"
$Py      = "python"
if (Test-Path $PyVenv) { $Py = $PyVenv }


# pythonw для фонового запуска (без консольного окна)
$PyW  = Join-Path $BotDir ".venv\Scripts\pythonw.exe"
$PyBg = $Py
if (Test-Path $PyW) { $PyBg = $PyW }


$AppLog      = Join-Path $BotDir "logs\app.log"
$LauncherLog = Join-Path $BotDir "launcher.log"
$StopFile    = Join-Path $BotDir "stop.request"
$OrdersJson  = Join-Path $BotDir "orders.json"
$AdminJson   = Join-Path $BotDir "admin_chat.json"
$HealthPs1   = Join-Path $BotDir "healthcheck.ps1"


function Get-BotProcs {
  if (!(Test-Path $Main)) { return @() }
  $procs = Get-CimInstance Win32_Process | Where-Object {
    $_.CommandLine -and ($_.CommandLine -like "*$Main*")
  }
  return @($procs)
}


function Is-Running { return ((Get-BotProcs).Count -gt 0) }


function Show-Status {
  Section "Status"
  if (Is-Running) {
    $pids = (Get-BotProcs | Select-Object -ExpandProperty ProcessId) -join ","
    OK ("RUNNING pid=" + $pids)
  } else {
    WARN "NOT RUNNING"
  }
}


function Start-Bot {
  Section "Start"
  if (Is-Running) { WARN "Already running"; return }


  if (!(Test-Path $Main)) { FAIL "main.py not found"; exit 2 }


  if ($Foreground) {
    OK "Starting in foreground..."
    & $Py $Main
    return
  }


  Start-Process -WindowStyle Hidden -FilePath $PyBg -ArgumentList @($Main) -WorkingDirectory $BotDir | Out-Null
  OK "Started in background"
}


function Stop-Bot {
  Section "Stop"
  if (!(Is-Running)) { WARN "Not running"; return }


  $acked = $false
  $client = $null
  $stream = $null


  try {
    $client = New-Object System.Net.Sockets.TcpClient
    $iar = $client.BeginConnect($StopTcpHost, $StopTcpPort, $null, $null)
    if (!$iar.AsyncWaitHandle.WaitOne($StopTimeoutMs)) { throw "connect timeout" }
    $client.EndConnect($iar) | Out-Null


    $client.ReceiveTimeout = $StopTimeoutMs
    $stream = $client.GetStream()


    # В main.py принимаются "", STOP/QUIT/EXIT и отвечается OK
    $bytes = [Text.Encoding]::UTF8.GetBytes("STOP`n")
    $stream.Write($bytes, 0, $bytes.Length)
    $stream.Flush()


    $buf = New-Object byte[] 32
    $n = $stream.Read($buf, 0, $buf.Length)
    $resp = ""
    if ($n -gt 0) { $resp = [Text.Encoding]::UTF8.GetString($buf, 0, $n).Trim() }


    if ($resp -eq "OK") { $acked = $true }
  } catch {
    $acked = $false
  } finally {
    try { if ($stream) { $stream.Dispose() } } catch {}
    try { if ($client) { $client.Close() } } catch {}
  }


  if ($acked) {
    OK "TCP STOP ACK=OK"
  } else {
    WARN "TCP STOP no-ack -> fallback stop.request"
    New-Item -ItemType File -Path $StopFile -Force | Out-Null
  }


  # ждём остановку до ~20 секунд
  for ($i=0; $i -lt 40; $i++) {
    Start-Sleep -Milliseconds 500
    if (!(Is-Running)) { OK "Stopped"; return }
  }
  if ($Force) {
    WARN "Force stop: killing bot process(es)"
    $procs = Get-BotProcs
    if ($procs.Count -gt 0) {
      $pids = ($procs | Select-Object -ExpandProperty ProcessId) -join ","
      WARN ("Killing PID(s): " + $pids)
      $procs | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
    }
    # ждём завершение ещё до ~10 секунд
    for ($j=0; $j -lt 20; $j++) {
      Start-Sleep -Milliseconds 500
      if (!(Is-Running)) { OK "Force-stopped"; return }
    }
    FAIL "Force stop failed (still running)"
    return
  }

  WARN "Still running (check logs)"
}


function Restart-Bot {
  Section "Restart"
  Stop-Bot
  Start-Sleep -Seconds 2
  Start-Bot
}


function Tail-Log {
  Section ("Tail log (" + $Log + ")")
  $p = $AppLog
  if ($Log -eq "launcher") { $p = $LauncherLog }


  if (!(Test-Path $p)) { WARN ("Missing log: " + $p); return }


  if ($Follow) {
    Get-Content -Path $p -Tail $Tail -Encoding UTF8 -Wait
  } else {
    Get-Content -Path $p -Tail $Tail -Encoding UTF8
  }
}


function Run-Health([switch]$Fix) {
  Section "Healthcheck"
  if (!(Test-Path $HealthPs1)) { WARN "healthcheck.ps1 not found"; return }
  if ($Fix) {
    & powershell -ExecutionPolicy Bypass -File $HealthPs1 -Tail $Tail -FixJson
  } else {
    & powershell -ExecutionPolicy Bypass -File $HealthPs1 -Tail $Tail
  }
}


function Backup-Json {
  Section "Backup JSON"
  $stamp = Get-Date -Format "yyyyMMdd_HHmmss"
  foreach ($p in @($OrdersJson, $AdminJson)) {
    if (Test-Path $p) {
      $bak = ($p + "." + $stamp + ".bak")
      Copy-Item -Force $p $bak
      OK ("Backup: " + (Split-Path $p -Leaf) + " -> " + (Split-Path $bak -Leaf))
    } else {
      WARN ("Missing: " + (Split-Path $p -Leaf))
    }
  }
}


switch ($Action) {
  "status"   { Show-Status }
  "start"    { Start-Bot }
  "stop"     { Stop-Bot }
  "restart"  { Restart-Bot }
  "tail"     { Tail-Log }
  "health"   { Run-Health }
  "fixjson"  { Run-Health -Fix }
  "backup"   { Backup-Json }
}