@echo off
chcp 65001 >nul
setlocal

set "ROOT=%~dp0"
set "CPOLAR_DIR=D:\cpolar"
set "CPOLAR_EXE=%CPOLAR_DIR%\cpolar.exe"

echo ========================================
echo   SecLab local backend one-click start
echo ========================================
echo.
echo This script starts the local services used for development:
echo - Docker lab containers: 8090-8095
echo - user-service: 8083
echo - experiment-module-service: 8084
echo - ai-agent-service: 8010
echo - cpolar tunnel for ai-agent-service: public https URL -> 8010
echo.

echo [1/6] Starting Docker lab containers...
docker compose -f "%ROOT%sqli-lab\docker-compose.yml" up -d
docker compose -f "%ROOT%xss-lab\docker-compose.yml" up -d
docker compose -f "%ROOT%csrf-lab\docker-compose.yml" up -d
docker compose -f "%ROOT%file-upload-lab\docker-compose.yml" up -d
docker compose -f "%ROOT%directory-traversal-lab\docker-compose.yml" up -d
docker compose -f "%ROOT%command-inject\docker-compose.yml" up -d
echo.

echo [2/6] Starting sec-code container on 8080...
docker stop sec-code-container 2>nul
docker rm sec-code-container 2>nul
docker run -d --name sec-code-container -p 8080:80 gsycl2004/sec-code
echo.

echo [3/6] Starting user-service on 8083...
netstat -ano | findstr /R /C:":8083 .*LISTENING" >nul
if errorlevel 1 (
    start "SecLab user-service 8083" /D "%ROOT%user-service" cmd /k ".\gradlew.bat bootRun"
) else (
    echo user-service already appears to be listening on 8083, skipping.
)
echo.

echo [4/6] Starting experiment-module-service on 8084...
netstat -ano | findstr /R /C:":8084 .*LISTENING" >nul
if errorlevel 1 (
    start "SecLab experiment-module-service 8084" /D "%ROOT%experiment-module-service" cmd /k ".\gradlew.bat bootRun"
) else (
    echo experiment-module-service already appears to be listening on 8084, skipping.
)
echo.

echo [5/6] Starting ai-agent-service on 8010...
netstat -ano | findstr /R /C:":8010 .*LISTENING" >nul
if errorlevel 1 (
    start "SecLab AI Agent 8010" /D "%ROOT%ai-agent-service" cmd /k "python main.py"
) else (
    echo ai-agent-service already appears to be listening on 8010, skipping.
)
echo.

echo [6/6] Starting cpolar tunnel to ai-agent-service 8010...
if exist "%CPOLAR_EXE%" (
    start "SecLab cpolar 8010" /D "%CPOLAR_DIR%" cmd /k ".\cpolar.exe http 8010"
) else (
    echo cpolar not found: %CPOLAR_EXE%
    echo Start it manually if needed: cpolar http 8010
)
echo.

echo ========================================
echo   Started. Keep the opened windows alive.
echo ========================================
echo.
echo Local checks:
echo   curl http://127.0.0.1:8010/health
echo   curl http://127.0.0.1:8010/api/docker/list
echo   curl http://127.0.0.1:8083/stu/login
echo   curl http://127.0.0.1:8084/course/overview-list
echo.
echo Lab URLs:
echo   SQL injection:          http://localhost:8091
echo   XSS:                    http://localhost:8092
echo   CSRF:                   http://localhost:8093
echo   File upload:            http://localhost:8094
echo   Directory traversal:    http://localhost:8095
echo   Command injection:      http://localhost:8090
echo   Secure code container:  http://localhost:8080
echo.
echo For Dify/cpolar:
echo   Copy the latest "Forwarding https://..." URL from the cpolar window.
echo   Send that URL as the Dify tool Base URL.
echo.
pause
