@echo off
REM Start nanobot gateway in background using PowerShell

powershell -ExecutionPolicy Bypass -File "%~dp0nanobot-service.ps1" start
