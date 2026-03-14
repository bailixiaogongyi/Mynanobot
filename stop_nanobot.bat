@echo off
REM Stop nanobot gateway service using PowerShell

powershell -ExecutionPolicy Bypass -File "%~dp0nanobot-service.ps1" stop
