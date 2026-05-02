@echo off
echo Остановка CRM...
cd /d "%~dp0infra"
docker-compose down
echo CRM остановлен.
pause
