@echo off
powershell -ExecutionPolicy Bypass -File scripts\init-review.ps1
if errorlevel 1 exit /b 1
docker compose -f docker-compose.review.yml up --build
