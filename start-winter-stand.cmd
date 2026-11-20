@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0winter_stand\start.ps1"
if errorlevel 1 pause
