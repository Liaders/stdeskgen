@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0winter_lab\start.ps1" -Profile
if errorlevel 1 pause
