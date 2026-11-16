@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0toolbar_stand\start.ps1"
if errorlevel 1 pause
