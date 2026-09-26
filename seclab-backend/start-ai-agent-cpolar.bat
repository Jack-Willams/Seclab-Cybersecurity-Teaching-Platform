@echo off
chcp 65001 >nul
setlocal

set "ROOT=%~dp0"
set "AGENT_DIR=%ROOT%ai-agent-service"
set "CPOLAR_DIR=D:\cpolar"
set "CPOLAR_EXE=%CPOLAR_DIR%\cpolar.exe"
if "%MYSQL_HOST%"=="" set "MYSQL_HOST=127.0.0.1"
if "%MYSQL_PORT%"=="" set "MYSQL_PORT=3306"
if "%MYSQL_USER%"=="" set "MYSQL_USER=seclab_app"
if "%MYSQL_PASSWORD%"=="" set "MYSQL_PASSWORD=Seclab@123"
if "%MYSQL_DATABASE%"=="" set "MYSQL_DATABASE=seclab_profile"

echo ========================================
echo   Start SecLab AI Agent + cpolar
echo ========================================
echo.

if not exist "%AGENT_DIR%\main.py" (
    echo Cannot find ai-agent-service main.py:
    echo %AGENT_DIR%\main.py
    pause
    exit /b 1
)

echo [1/2] Starting AI Agent service on 8010...
netstat -ano | findstr /R /C:":8010 .*LISTENING" >nul
if not errorlevel 1 (
    echo AI Agent already appears to be listening on 8010, skipping duplicate start.
) else (
    if exist "%AGENT_DIR%\venv\Scripts\activate.bat" (
        start "SecLab AI Agent 8010" /D "%AGENT_DIR%" cmd /k "set MYSQL_HOST=%MYSQL_HOST%&& set MYSQL_PORT=%MYSQL_PORT%&& set MYSQL_USER=%MYSQL_USER%&& set MYSQL_PASSWORD=%MYSQL_PASSWORD%&& set MYSQL_DATABASE=%MYSQL_DATABASE%&& call venv\Scripts\activate.bat && python main.py"
    ) else if exist "%AGENT_DIR%\.venv\Scripts\activate.bat" (
        start "SecLab AI Agent 8010" /D "%AGENT_DIR%" cmd /k "set MYSQL_HOST=%MYSQL_HOST%&& set MYSQL_PORT=%MYSQL_PORT%&& set MYSQL_USER=%MYSQL_USER%&& set MYSQL_PASSWORD=%MYSQL_PASSWORD%&& set MYSQL_DATABASE=%MYSQL_DATABASE%&& call .venv\Scripts\activate.bat && python main.py"
    ) else (
        echo No venv found. Using current Python from PATH.
        start "SecLab AI Agent 8010" /D "%AGENT_DIR%" cmd /k "set MYSQL_HOST=%MYSQL_HOST%&& set MYSQL_PORT=%MYSQL_PORT%&& set MYSQL_USER=%MYSQL_USER%&& set MYSQL_PASSWORD=%MYSQL_PASSWORD%&& set MYSQL_DATABASE=%MYSQL_DATABASE%&& python main.py"
    )
)

echo [2/2] Starting cpolar tunnel to 8010...
if exist "%CPOLAR_EXE%" (
    start "SecLab cpolar 8010" /D "%CPOLAR_DIR%" cmd /k ".\cpolar.exe http 8010"
) else (
    echo Cannot find cpolar:
    echo %CPOLAR_EXE%
    echo Please edit CPOLAR_DIR in this script or start cpolar manually.
)

echo.
echo Started. Keep the two opened windows alive.
echo.
echo Local checks:
echo   curl http://127.0.0.1:8010/health
echo   curl http://127.0.0.1:8010/api/docker/list
echo.
echo Dify/cpolar:
echo   Copy the latest "Forwarding https://..." URL from the cpolar window.
echo   Send that URL to the Dify operator as the tool Base URL.
echo.
pause
