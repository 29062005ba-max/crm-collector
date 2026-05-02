@echo off
echo Generating SSL certificate for localhost and 192.168.8.222...
if not exist ssl mkdir ssl
docker run --rm -v "%CD%\ssl:/ssl" alpine/openssl req -x509 -nodes -days 3650 -newkey rsa:2048 -keyout /ssl/key.pem -out /ssl/cert.pem -subj "/C=KZ/ST=Almaty/L=Almaty/O=CRM/CN=localhost" -addext "subjectAltName=IP:127.0.0.1,IP:192.168.8.222,DNS:localhost"
echo SSL certificate generated!
pause
