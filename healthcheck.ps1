param(
    [int]$Tail = 80,
    [switch]$FixJson
)

$ErrorActionPreference = "Stop"

function Write-Section([string]$t) { Write-Host ""; Write-Host ("==== {0} ====" -f $t) }
function OK([string]$t)   { Write-Host ("[OK]   {0}" -f $t) }
function WARN([string]$t) { Write-Host ("[WARN] {0}" -f $t) }
function FAIL([string]$t) { Write-Host ("[FAIL] {0}" -f $t) }

$BotDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $BotDir

$Main   = Join-Path $BotDir "main.py"
$PyVenv = Join-Path $BotDir ".venv\Scripts\python.exe"
$Py     = if (Test-Path $PyVenv) { $PyVenv } else { "python" }

function Backup-File([string]$Path) {
    $ts  = Get-Date -Format "yyyyMMdd_HHmmss"
    $bak = "$Path.bak_$ts"
    Copy-Item -Force $Path $bak
    OK ("backup -> {0}" -f $bak)
}

function Ensure-Json([string]$Path, [string]$DefaultJson) {
    $name = Split-Path $Path -Leaf

    if (!(Test-Path $Path)) {
        WARN ("missing: {0}" -f $name)
        if ($FixJson) {
            $DefaultJson | Set-Content -Encoding UTF8 -NoNewline $Path
            OK ("created default: {0}" -f $name)
        }
        return
    }

    $raw = ""
    try { $raw = Get-Content -Raw -Encoding UTF8 $Path } catch { WARN ("cannot read: {0}" -f $name); return }

    if ($raw.Trim().Length -eq 0) {
        WARN ("empty: {0}" -f $name)
        if ($FixJson) {
            Backup-File $Path
            $DefaultJson | Set-Content -Encoding UTF8 -NoNewline $Path
            OK ("written default: {0}" -f $name)
        }
        return
    }

    try {
        $null = $raw | ConvertFrom-Json
        $fi = Get-Item $Path
        OK ("json OK: {0} ({1} bytes, mtime {2})" -f $name, $fi.Length, $fi.LastWriteTime)
    } catch {
        WARN ("json BAD: {0} ({1})" -f $name, $_.Exception.Message)
        if ($FixJson) {
            Backup-File $Path
            $DefaultJson | Set-Content -Encoding UTF8 -NoNewline $Path
            OK ("fixed: {0}" -f $name)
        }
    }
}

Write-Section "Paths"
OK ("BotDir = {0}" -f $BotDir)
OK ("Python = {0}" -f $Py)
OK ("Main   = {0}" -f $Main)

Write-Section "Python compile"
if (!(Test-Path $Main)) { FAIL "main.py is missing"; exit 2 }
try {
    & $Py -m py_compile $Main | Out-Null
    OK "py_compile OK"
} catch {
    FAIL ("py_compile FAILED: {0}" -f $_.Exception.Message)
    exit 3
}

Write-Section "JSON files"
Ensure-Json (Join-Path $BotDir "orders.json") "{}"
Ensure-Json (Join-Path $BotDir "admin_chat.json") '{"admin_chat_id":0}'

Write-Section "Key files"
$files = @(".env","logs\app.log","launcher.log","admin_chat.json","orders.json")
foreach ($f in $files) {
    $p = Join-Path $BotDir $f
    if (Test-Path $p) {
        $fi = Get-Item $p
        OK ("{0} : {1} bytes, mtime {2}" -f $f, $fi.Length, $fi.LastWriteTime)
    } else {
        WARN ("missing: {0}" -f $f)
    }
}

Write-Section ("Tail logs (last {0})" -f $Tail)
$AppLog = Join-Path $BotDir "logs\app.log"
if (Test-Path $AppLog) {
    try { Get-Content -Path $AppLog -Tail $Tail -Encoding UTF8 } catch { WARN ("cannot tail logs\app.log: {0}" -f $_.Exception.Message) }
} else {
    WARN "logs\app.log missing"
}

Write-Section "Done"
Write-Host "Tip: run with -Tail 200 or -FixJson"
exit 0
