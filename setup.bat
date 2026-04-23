@echo off
setlocal
chcp 65001 >nul

set "APP_DIR=%~dp0"
cd /d "%APP_DIR%"

echo [AI Thread App] Setting up Python environment...

if exist "%APP_DIR%venv\Scripts\python.exe" (
    echo Existing virtual environment found.
    goto install_dependencies
)

where py >nul 2>nul
if %ERRORLEVEL%==0 (
    set "PY_CMD=py -3"
    goto create_venv
)

where python >nul 2>nul
if %ERRORLEVEL%==0 (
    set "PY_CMD=python"
    goto create_venv
)

echo.
echo Python 3 was not found on this PC.
echo Please install Python 3.11 or newer from:
echo https://www.python.org/downloads/
echo.
pause
exit /b 1

:create_venv
echo Creating virtual environment...
%PY_CMD% -m venv "%APP_DIR%venv"
if errorlevel 1 (
    echo Failed to create virtual environment.
    pause
    exit /b 1
)

:install_dependencies
echo Installing/updating dependencies...
"%APP_DIR%venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 (
    echo Failed to upgrade pip.
    pause
    exit /b 1
)

"%APP_DIR%venv\Scripts\python.exe" -m pip install -r "%APP_DIR%requirements.txt"
if errorlevel 1 (
    echo Failed to install dependencies.
    pause
    exit /b 1
)

echo.
echo Setup complete.
exit /b 0
