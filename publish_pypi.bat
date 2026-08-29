@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0publish_pypi.ps1"
pause
