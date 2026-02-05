@echo off
setlocal EnableExtensions

set "BOT_DIR=C:\GRUZO2\gruzo2_bot"
set "MAIN=%BOT_DIR%\main.py"
set "LAUNCHLOG=%BOT_DIR%\launcher.log"

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ErrorActionPreference='SilentlyContinue';" ^
  "$main=$env:MAIN; $launch=$env:LAUNCHLOG;" ^
  "if(!(Test-Path $launch)){ New-Item -ItemType File -Path $launch -Force | Out-Null }" ^
  "$procs=Get-CimInstance Win32_Process | Where-Object { $_.Name -in @('python.exe','pythonw.exe') -and $_.CommandLine -like ('*'+$main+'*') };" ^
  "$k=0; foreach($p in $procs){ try{ Stop-Process -Id $p.ProcessId -Force; $k++ } catch {} }" ^
  "$msg=('[{0}] STOP_BOT clicked (killed {1})' -f (Get-Date -Format 'dd.MM.yyyy HH:mm:ss'), $k);" ^
  "Add-Content -Path $launch -Value $msg -Encoding UTF8"

exit /b 0
