@echo off
echo ========================================
echo    CRM Collector - Запуск системы
echo ========================================
echo.

cd /d "%~dp0infra"

REM Check if SSL exists
if not exist ssl\cert.pem (
    echo Генерация SSL сертификата...
    call generate-ssl.bat
)

echo Запуск CRM...
docker-compose up -d

echo.
echo ========================================
echo  CRM запущен!
echo  Откройте: https://localhost
echo  Логин: admin@crm.local
echo  Пароль: Admin1234!
echo ========================================
pause
