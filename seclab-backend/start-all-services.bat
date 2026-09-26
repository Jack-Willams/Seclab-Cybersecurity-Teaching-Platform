@echo off
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0"

REM SecLab all backend local startup script.
REM Default local mode:
REM - user-service login/register backend runs with Gradle bootRun on port 8083.
REM - Docker microservice images are started only if they already exist locally.
REM
REM Optional switches:
REM   set START_LOCAL_USER_SERVICE=false   Use Docker user-service on 8081 instead.
REM   set START_LOCAL_EXPERIMENT_MODULE_SERVICE=false   Use Docker experiment-module-service instead.
REM   set START_LOCAL_IMAGE_SERVICE=false          Use Docker image-service instead of local gradlew.
REM   set START_AI_AGENT=false             Do not start ai-agent-service on 8010.
REM   set START_CPOLAR=true                Also open cpolar tunnel for ai-agent-service.

if "%START_LOCAL_USER_SERVICE%"=="" set "START_LOCAL_USER_SERVICE=true"
if "%START_LOCAL_EXPERIMENT_MODULE_SERVICE%"=="" set "START_LOCAL_EXPERIMENT_MODULE_SERVICE=true"
if "%START_LOCAL_IMAGE_SERVICE%"=="" set "START_LOCAL_IMAGE_SERVICE=true"
if "%START_AI_AGENT%"=="" set "START_AI_AGENT=true"
if "%START_CPOLAR%"=="" set "START_CPOLAR=false"
if "%USER_SERVICE_DB_HOST%"=="" set "USER_SERVICE_DB_HOST=127.0.0.1"
if "%USER_SERVICE_DB_PORT%"=="" set "USER_SERVICE_DB_PORT=3306"
if "%USER_SERVICE_DB_NAME%"=="" set "USER_SERVICE_DB_NAME=userservice"
if "%USER_SERVICE_DB_USERNAME%"=="" set "USER_SERVICE_DB_USERNAME=seclab_app"
if "%USER_SERVICE_DB_PASSWORD%"=="" set "USER_SERVICE_DB_PASSWORD=Seclab@123"
if "%PROFILE_DB_NAME%"=="" set "PROFILE_DB_NAME=seclab_profile"

set "CPOLAR_DIR=D:\cpolar"
set "CPOLAR_EXE=%CPOLAR_DIR%\cpolar.exe"

echo ========================================
echo   SecLab all backend one-click startup
echo ========================================
echo.
echo Working directory: %CD%
echo Local user-service mode: %START_LOCAL_USER_SERVICE%
echo Local experiment-module-service mode: %START_LOCAL_EXPERIMENT_MODULE_SERVICE%
echo Local image-service mode: %START_LOCAL_IMAGE_SERVICE%
echo user-service DB: %USER_SERVICE_DB_HOST%:%USER_SERVICE_DB_PORT%/%USER_SERVICE_DB_NAME%
echo profile DB:      %USER_SERVICE_DB_HOST%:%USER_SERVICE_DB_PORT%/%PROFILE_DB_NAME%
echo AI Agent startup: %START_AI_AGENT%
echo cpolar startup: %START_CPOLAR%
echo.

echo [1/13] Starting SQL injection lab on 8091...
call :start_sqli_lab

echo [2/13] Starting XSS lab on 8092...
call :compose_up "xss-lab"

echo [3/13] Starting CSRF lab on 8093...
call :compose_up "csrf-lab"

echo [4/13] Starting file upload lab on 8094...
call :compose_up "file-upload-lab"

echo [5/13] Starting directory traversal lab on 8095...
call :compose_up "directory-traversal-lab"

echo [6/13] Starting command injection lab on 8090...
call :compose_up "command-inject"

echo [7/13] Starting protocol analysis lab on 8896...
call :compose_up "protocol-analysis-lab"

echo [8/13] Starting Eureka registry if image exists...
call :run_image_if_exists "saclab-eureka" "saclab-eureka" "8761:8761" "" ""

echo [9/13] Starting Gateway if image exists...
call :run_image_if_exists "saclab-gateway" "saclab-gateway" "8085:8085" "saclab-eureka" "EUREKA_CLIENT_SERVICEURL_DEFAULTZONE=http://saclab-eureka:8761/eureka/"

echo [10/13] Starting user-service login/register backend...
if /I "%START_LOCAL_USER_SERVICE%"=="true" (
    call :start_local_user_service
) else (
    call :run_image_if_exists "saclab-user-service" "saclab-user-service" "8081:8081" "saclab-eureka" "EUREKA_CLIENT_SERVICEURL_DEFAULTZONE=http://saclab-eureka:8761/eureka/"
)

echo [11/13] Starting experiment-module-service...
if /I "%START_LOCAL_EXPERIMENT_MODULE_SERVICE%"=="true" (
    call :start_local_experiment_module_service
) else (
    call :run_image_if_exists "saclab-experiment-module-service" "saclab-experiment-module-service" "8084:8084" "saclab-eureka" "EUREKA_CLIENT_SERVICEURL_DEFAULTZONE=http://saclab-eureka:8761/eureka/"
)

echo [12/13] Starting image-service on 8086...
REM image-service 自身监听 8086 (application.properties: server.port=8086)。
REM 旧脚本这里写的是 8083:8083, 既和 user-service 抢端口, 也和服务实际端口不符。
REM 而且只在本地已有 Docker 镜像时才起, 实际上从来没跑起来过, 于是注册页和
REM 个人资料页的头像上传一直连不上 8086, 全库没有一个用户存下过头像。
if /I "%START_LOCAL_IMAGE_SERVICE%"=="true" (
    call :start_local_image_service
) else (
    call :run_image_if_exists "saclab-image-service" "saclab-image-service" "8086:8086" "saclab-eureka" "EUREKA_CLIENT_SERVICEURL_DEFAULTZONE=http://saclab-eureka:8761/eureka/"
)

echo [13/13] Starting docker-service if image exists...
call :run_image_if_exists "saclab-docker-service" "saclab-docker-service" "8087:8087" "saclab-eureka" "EUREKA_CLIENT_SERVICEURL_DEFAULTZONE=http://saclab-eureka:8761/eureka/"

echo [extra] Starting Docker API server on 3000...
call :start_docker_api

echo [extra] Starting secure code container on 8080...
docker stop sec-code-container 2>nul
docker rm sec-code-container 2>nul
docker run -d --name sec-code-container -p 8080:80 gsycl2004/sec-code
echo.

if /I "%START_AI_AGENT%"=="true" (
    echo [extra] Starting AI Agent service on 8010...
    call :start_ai_agent
)

if /I "%START_CPOLAR%"=="true" (
    echo [extra] Starting cpolar tunnel to AI Agent 8010...
    call :start_cpolar
) else (
    echo [extra] cpolar is not started by default.
    echo         To start it too: set START_CPOLAR=true then run this script again.
)

echo.
echo ========================================
echo   Startup commands have been issued
echo ========================================
echo.
echo Core local backend:
echo - user-service login/register: http://localhost:8083
echo - Docker API for lab buttons:   http://localhost:3000/health
echo - AI Agent service:            http://localhost:8010
echo - AI Agent health:             http://localhost:8010/health
echo - AI Docker tool list:         http://localhost:8010/api/docker/list
echo.
echo Docker microservices, if local images exist:
echo - Eureka:                      http://localhost:8761
echo - Gateway:                     http://localhost:8085
echo - experiment-module-service:   http://localhost:8084
echo - docker-service:              http://localhost:8087
echo - image-service:               http://localhost:8086
echo.
echo Lab URLs:
echo - SQL injection:               http://localhost:8091
echo - XSS:                         http://localhost:8092
echo - CSRF:                        http://localhost:8093
echo - File upload:                 http://localhost:8094
echo - Directory traversal:         http://localhost:8095
echo - Command injection:           http://localhost:8090
echo - Secure code container:       http://localhost:8080
echo.
echo Frontend is not started here. Start it manually:
echo   cd D:\Seclab\SecLab-Combined\SecLab-FrontEnd-2
echo   npm run dev
echo.
echo Useful checks:
echo   curl http://127.0.0.1:8083/stu/login
echo   curl http://127.0.0.1:3000/health
echo   curl http://127.0.0.1:3000/api/docker/target-status/sqli
echo   curl http://127.0.0.1:8010/health
echo   curl http://127.0.0.1:8010/api/docker/list
echo   docker ps
echo.
pause
exit /b 0

:compose_up
set "LAB_DIR=%~1"
if exist "%CD%\%LAB_DIR%\docker-compose.yml" (
    docker compose -f "%CD%\%LAB_DIR%\docker-compose.yml" up -d
) else (
    echo WARNING: %LAB_DIR%\docker-compose.yml not found, skipped.
)
exit /b 0

:start_sqli_lab
if exist "%CD%\sqli-lab\docker-compose.yml" (
    REM Keep this explicit: user expects this exact startup path for SQLi lab.
    docker compose -f sqli-lab/docker-compose.yml up -d
) else (
    echo WARNING: sqli-lab\docker-compose.yml not found, skipped.
)
exit /b 0

:run_image_if_exists
set "IMAGE_NAME=%~1"
set "CONTAINER_NAME=%~2"
set "PORT_MAP=%~3"
set "LINK_NAME=%~4"
set "ENV_PAIR=%~5"

docker image inspect "%IMAGE_NAME%" >nul 2>nul
if errorlevel 1 (
    echo SKIP: Docker image "%IMAGE_NAME%" not found locally.
    echo       Build service images first if this service is required.
    exit /b 0
)

docker stop "%CONTAINER_NAME%" 2>nul
docker rm "%CONTAINER_NAME%" 2>nul

if "%LINK_NAME%"=="" (
    docker run -d --name "%CONTAINER_NAME%" -p "%PORT_MAP%" -e "JAVA_OPTS=-Djava.security.egd=file:/dev/./urandom" "%IMAGE_NAME%"
) else (
    docker run -d --name "%CONTAINER_NAME%" -p "%PORT_MAP%" -e "%ENV_PAIR%" -e "JAVA_OPTS=-Djava.security.egd=file:/dev/./urandom" --link "%LINK_NAME%" "%IMAGE_NAME%"
)
exit /b 0

:start_local_user_service
netstat -ano | findstr /R /C:":8083 .*LISTENING" >nul
if not errorlevel 1 (
    echo user-service already appears to be listening on 8083, skipping bootRun start.
    exit /b 0
)

if not exist "%CD%\user-service\gradlew.bat" (
    echo ERROR: user-service Gradle wrapper not found: %CD%\user-service\gradlew.bat
    echo Login/register backend was NOT started.
    exit /b 1
)

start "SecLab user-service login-register 8083" /D "%CD%\user-service" cmd /k "set USER_SERVICE_DB_HOST=%USER_SERVICE_DB_HOST%&& set USER_SERVICE_DB_PORT=%USER_SERVICE_DB_PORT%&& set USER_SERVICE_DB_NAME=%USER_SERVICE_DB_NAME%&& set USER_SERVICE_DB_USERNAME=%USER_SERVICE_DB_USERNAME%&& set USER_SERVICE_DB_PASSWORD=%USER_SERVICE_DB_PASSWORD%&& .\gradlew.bat bootRun"
echo Keep the "SecLab user-service login-register 8083" window open.
echo Waiting for local user-service startup on http://localhost:8083 ...
timeout /t 12 /nobreak >nul
exit /b 0

:start_local_experiment_module_service
netstat -ano | findstr /R /C:":8084 .*LISTENING" >nul
if not errorlevel 1 (
    echo experiment-module-service already appears to be listening on 8084, skipping bootRun start.
    exit /b 0
)

if not exist "%CD%\experiment-module-service\gradlew.bat" (
    echo ERROR: experiment-module-service Gradle wrapper not found: %CD%\experiment-module-service\gradlew.bat
    echo Course and module backend was NOT started.
    exit /b 1
)

start "SecLab experiment-module-service 8084" /D "%CD%\experiment-module-service" cmd /k "set EXPERIMENT_MODULE_DB_HOST=%USER_SERVICE_DB_HOST%&& set EXPERIMENT_MODULE_DB_PORT=%USER_SERVICE_DB_PORT%&& set EXPERIMENT_MODULE_DB_USERNAME=%USER_SERVICE_DB_USERNAME%&& set EXPERIMENT_MODULE_DB_PASSWORD=%USER_SERVICE_DB_PASSWORD%&& .\gradlew.bat bootRun"
echo Keep the "SecLab experiment-module-service 8084" window open.
echo Waiting for experiment-module-service startup on http://localhost:8084 ...
timeout /t 12 /nobreak >nul
exit /b 0

:start_local_image_service
netstat -ano | findstr /R /C:":8086 .*LISTENING" >nul
if not errorlevel 1 (
    echo image-service already appears to be listening on 8086, skipping bootRun start.
    exit /b 0
)

if not exist "%CD%\image-service\gradlew.bat" (
    echo ERROR: image-service Gradle wrapper not found: %CD%\image-service\gradlew.bat
    echo Avatar upload was NOT started.
    exit /b 1
)

start "SecLab image-service 8086" /D "%CD%\image-service" cmd /k ".\gradlew.bat bootRun"
echo Keep the "SecLab image-service 8086" window open.
echo Waiting for image-service startup on http://localhost:8086 ...
timeout /t 12 /nobreak >nul
exit /b 0

:start_docker_api
netstat -ano | findstr /R /C:":3000 .*LISTENING" >nul
if not errorlevel 1 (
    echo Docker API server already appears to be listening on 3000, skipping start.
    exit /b 0
)

if not exist "%CD%\docker-api-server.js" (
    echo WARNING: docker-api-server.js not found, lab button API skipped.
    exit /b 0
)

where npm >nul 2>nul
if errorlevel 1 (
    echo WARNING: npm was not found in PATH, Docker API server was NOT started.
    exit /b 0
)

if not exist "%CD%\node_modules\express" (
    echo Installing Docker API Node dependencies...
    call npm install
)

start "SecLab Docker API 3000" /D "%CD%" cmd /k "npm start"
echo Keep the "SecLab Docker API 3000" window open.
timeout /t 3 /nobreak >nul
exit /b 0

:start_ai_agent
netstat -ano | findstr /R /C:":8010 .*LISTENING" >nul
if not errorlevel 1 (
    echo ai-agent-service already appears to be listening on 8010, skipping start.
    exit /b 0
)

if not exist "%CD%\ai-agent-service\main.py" (
    echo WARNING: ai-agent-service\main.py not found, skipped.
    exit /b 0
)

if exist "%CD%\ai-agent-service\venv\Scripts\activate.bat" (
    start "SecLab AI Agent 8010" /D "%CD%\ai-agent-service" cmd /k "set MYSQL_HOST=%USER_SERVICE_DB_HOST%&& set MYSQL_PORT=%USER_SERVICE_DB_PORT%&& set MYSQL_USER=%USER_SERVICE_DB_USERNAME%&& set MYSQL_PASSWORD=%USER_SERVICE_DB_PASSWORD%&& set MYSQL_DATABASE=%PROFILE_DB_NAME%&& call venv\Scripts\activate.bat && python main.py"
) else if exist "%CD%\ai-agent-service\.venv\Scripts\activate.bat" (
    start "SecLab AI Agent 8010" /D "%CD%\ai-agent-service" cmd /k "set MYSQL_HOST=%USER_SERVICE_DB_HOST%&& set MYSQL_PORT=%USER_SERVICE_DB_PORT%&& set MYSQL_USER=%USER_SERVICE_DB_USERNAME%&& set MYSQL_PASSWORD=%USER_SERVICE_DB_PASSWORD%&& set MYSQL_DATABASE=%PROFILE_DB_NAME%&& call .venv\Scripts\activate.bat && python main.py"
) else (
    start "SecLab AI Agent 8010" /D "%CD%\ai-agent-service" cmd /k "set MYSQL_HOST=%USER_SERVICE_DB_HOST%&& set MYSQL_PORT=%USER_SERVICE_DB_PORT%&& set MYSQL_USER=%USER_SERVICE_DB_USERNAME%&& set MYSQL_PASSWORD=%USER_SERVICE_DB_PASSWORD%&& set MYSQL_DATABASE=%PROFILE_DB_NAME%&& python main.py"
)
echo Keep the "SecLab AI Agent 8010" window open.
timeout /t 3 /nobreak >nul
exit /b 0

:start_cpolar
if not exist "%CPOLAR_EXE%" (
    echo WARNING: cpolar not found: %CPOLAR_EXE%
    exit /b 0
)
start "SecLab cpolar 8010" /D "%CPOLAR_DIR%" cmd /k ".\cpolar.exe http 8010"
echo Copy the latest "Forwarding https://..." URL from the cpolar window for Dify.
exit /b 0

