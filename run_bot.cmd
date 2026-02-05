@echo off
setlocal EnableExtensions

set "BOT_DIR=C:\GRUZO2\gruzo2_bot"
set "PYW=%BOT_DIR%\.venv\Scripts\pythonw.exe"
set "MAIN=%BOT_DIR%\main.py"
set "LAUNCHLOG=%BOT_DIR%\launcher.log"
set "MUTEX=Local\GRUZO2_BOT_LOCK"

cd /d "%BOT_DIR%"

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ErrorActionPreference='Stop';" ^
  "$botDir=$env:BOT_DIR; $pyw=$env:PYW; $main=$env:MAIN; $launch=$env:LAUNCHLOG; $mutexName=$env:MUTEX;" ^
  "if(!(Test-Path $launch)){ New-Item -ItemType File -Path $launch -Force | Out-Null }" ^
  "$created=$false; $m=New-Object System.Threading.Mutex($false,$mutexName,[ref]$created);" ^
  "try{" ^
  "  if(-not $m.WaitOne(0)){" ^
  "    $msg=('[{0}] Already running. Exit.' -f (Get-Date -Format 'dd.MM.yyyy HH:mm:ss'));" ^
  "    Add-Content -Path $launch -Value $msg -Encoding UTF8 -ErrorAction SilentlyContinue;" ^
  "    exit 0;" ^
  "  }" ^
  "  $start=('[{0}] START' -f (Get-Date -Format 'dd.MM.yyyy HH:mm:ss'));" ^
  "  Add-Content -Path $launch -Value $start -Encoding UTF8 -ErrorAction SilentlyContinue;" ^
  "  $p=Start-Process -FilePath $pyw -ArgumentList @($main) -WorkingDirectory $botDir -PassThru;" ^
  "  $p.WaitForExit();" ^
  "  $code=$p.ExitCode;" ^
  "  $stop=('[{0}] STOP (code={1})' -f (Get-Date -Format 'dd.MM.yyyy HH:mm:ss'), $code);" ^
  "  Add-Content -Path $launch -Value $stop -Encoding UTF8 -ErrorAction SilentlyContinue;" ^
  "  exit $code;" ^
  "} catch {" ^
  "  $err=('[{0}] LAUNCHER ERROR: {1}' -f (Get-Date -Format 'dd.MM.yyyy HH:mm:ss'), $_.Exception.Message);" ^
  "  Add-Content -Path $launch -Value $err -Encoding UTF8 -ErrorAction SilentlyContinue;" ^
  "  exit 1;" ^
  "} finally {" ^
  "  try{ $m.ReleaseMutex() | Out-Null } catch {}" ^
  "  $m.Dispose()" ^
  "}"

exit /b %errorlevel%
