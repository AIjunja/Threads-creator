@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul

set "APP_DIR=%~dp0"
cd /d "%APP_DIR%"

echo [AI Thread App] Setting up Python environment...

if exist "%APP_DIR%venv\Scripts\python.exe" (
    echo Existing virtual environment found.
    goto install_dependencies
)

call :detect_python
if defined PY_CMD goto create_venv

call :install_python
if errorlevel 1 exit /b 1

call :detect_python
if defined PY_CMD goto create_venv

echo.
echo Python installation finished, but Python could not be found automatically.
echo Please restart this PC or install Python 3.11+ manually, then run run_app.bat again.
echo Download: https://www.python.org/downloads/
echo.
pause
exit /b 1

:detect_python
set "PY_CMD="

where py >nul 2>nul
if %ERRORLEVEL%==0 (
    py -3 --version >nul 2>nul
    if !ERRORLEVEL!==0 (
        set "PY_CMD=py -3"
        goto :eof
    )
)

where python >nul 2>nul
if %ERRORLEVEL%==0 (
    python --version >nul 2>nul
    if !ERRORLEVEL!==0 (
        set "PY_CMD=python"
        goto :eof
    )
)

for %%V in (314 313 312 311 310) do (
    if exist "%LocalAppData%\Programs\Python\Python%%V\python.exe" (
        set "PY_CMD=\"%LocalAppData%\Programs\Python\Python%%V\python.exe\""
        set "PATH=%LocalAppData%\Programs\Python\Python%%V;%LocalAppData%\Programs\Python\Launcher;!PATH!"
        goto :eof
    )
)

goto :eof

:install_python
where winget >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo.
    echo Python 3 was not found and winget is not available on this PC.
    echo Please install Python 3.11 or newer from:
    echo https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

echo.
echo Python 3 was not found. Installing automatically with winget...
winget install --id Python.Python.3.12 -e --source winget --accept-package-agreements --accept-source-agreements
if errorlevel 1 (
    echo.
    echo Automatic Python installation failed.
    echo Please install Python manually from:
    echo https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

echo Python installation finished. Checking installation...
exit /b 0

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
