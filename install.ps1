param(
    [string]$InstallDir = "$env:USERPROFILE\Threads-creator",
    [switch]$NoLaunch
)

$ErrorActionPreference = "Stop"
$RepoUrl = "https://github.com/AIjunja/Threads-creator.git"
$ZipUrl = "https://github.com/AIjunja/Threads-creator/archive/refs/heads/main.zip"

try {
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
} catch {
}

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "[Threads Creator] $Message" -ForegroundColor Cyan
}

function Test-Command {
    param([string]$Name)
    return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

function Refresh-Path {
    $machinePath = [Environment]::GetEnvironmentVariable("Path", "Machine")
    $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
    $env:Path = "$machinePath;$userPath"
}

function Install-WithWinget {
    param(
        [string]$PackageId,
        [string]$Name
    )

    if (-not (Test-Command "winget")) {
        Write-Host "winget is not available on this PC. Skipping automatic $Name install." -ForegroundColor Yellow
        return $false
    }

    Write-Step "Installing $Name with winget"
    winget install --id $PackageId -e --source winget --accept-package-agreements --accept-source-agreements
    Refresh-Path
    return $true
}

function Test-Python {
    if (Test-Command "py") {
        & py -3 --version *> $null
        if ($LASTEXITCODE -eq 0) {
            return $true
        }
    }

    if (Test-Command "python") {
        & python --version *> $null
        if ($LASTEXITCODE -eq 0) {
            return $true
        }
    }

    return $false
}

function Ensure-Python {
    if (Test-Python) {
        Write-Host "Python is ready."
        return
    }

    Install-WithWinget -PackageId "Python.Python.3.12" -Name "Python 3" | Out-Null

    if (-not (Test-Python)) {
        throw "Python 3 was not found and automatic installation failed. Install Python 3.11+ from https://www.python.org/downloads/ and run this installer again."
    }

    Write-Host "Python is ready."
}

function Ensure-Git {
    if (Test-Command "git") {
        Write-Host "Git is ready."
        return $true
    }

    Install-WithWinget -PackageId "Git.Git" -Name "Git" | Out-Null

    if (Test-Command "git") {
        Write-Host "Git is ready."
        return $true
    }

    Write-Host "Git is not available. The installer will download the repository ZIP instead." -ForegroundColor Yellow
    return $false
}

function Get-ScriptRoot {
    if ($PSScriptRoot) {
        return $PSScriptRoot
    }
    if ($PSCommandPath) {
        return Split-Path -Parent $PSCommandPath
    }
    return (Get-Location).Path
}

function Test-AppFolder {
    param([string]$Path)
    return (Test-Path (Join-Path $Path "run_app.bat")) -and (Test-Path (Join-Path $Path "requirements.txt"))
}

function Download-RepositoryZip {
    param([string]$TargetDir)

    Write-Step "Downloading Threads Creator without Git"
    $tempRoot = Join-Path $env:TEMP ("threads-creator-" + [Guid]::NewGuid().ToString("N"))
    $zipPath = Join-Path $tempRoot "threads-creator.zip"
    $extractDir = Join-Path $tempRoot "extract"

    New-Item -ItemType Directory -Force $tempRoot | Out-Null
    Invoke-WebRequest -Uri $ZipUrl -OutFile $zipPath
    Expand-Archive -Path $zipPath -DestinationPath $extractDir -Force

    $sourceDir = Get-ChildItem -Path $extractDir -Directory | Select-Object -First 1
    if (-not $sourceDir) {
        throw "Downloaded ZIP did not contain the app folder."
    }

    if (Test-Path $TargetDir) {
        $children = Get-ChildItem -Path $TargetDir -Force -ErrorAction SilentlyContinue
        if ($children) {
            throw "Install directory already exists and is not empty: $TargetDir"
        }
        Remove-Item $TargetDir -Recurse -Force
    }
    New-Item -ItemType Directory -Force (Split-Path -Parent $TargetDir) | Out-Null
    Move-Item -Path $sourceDir.FullName -Destination $TargetDir
    Remove-Item $tempRoot -Recurse -Force
}

function Install-Repository {
    $scriptRoot = Get-ScriptRoot
    if (Test-AppFolder $scriptRoot) {
        Write-Host "Running from existing app folder: $scriptRoot"
        return $scriptRoot
    }

    if (Test-AppFolder $InstallDir) {
        Write-Host "Existing app folder found: $InstallDir"
        return $InstallDir
    }

    $hasGit = Ensure-Git
    if ($hasGit) {
        Write-Step "Cloning Threads Creator"
        if (Test-Path $InstallDir) {
            if (Test-Path (Join-Path $InstallDir ".git")) {
                git -C $InstallDir pull --ff-only
                return $InstallDir
            }

            $children = Get-ChildItem -Path $InstallDir -Force -ErrorAction SilentlyContinue
            if ($children) {
                throw "Install directory already exists and is not empty: $InstallDir"
            }
        }

        git clone $RepoUrl $InstallDir
        return $InstallDir
    }

    Download-RepositoryZip -TargetDir $InstallDir
    return $InstallDir
}

try {
    Write-Step "Preparing installer"
    $appDir = Install-Repository
    Ensure-Python

    Write-Step "App folder"
    Write-Host $appDir

    if ($NoLaunch) {
        Write-Host "Install check completed. Launch skipped because -NoLaunch was provided."
        exit 0
    }

    Write-Step "Launching Threads Creator"
    Start-Process -FilePath (Join-Path $appDir "run_app.bat") -WorkingDirectory $appDir
} catch {
    Write-Host ""
    Write-Host "[Threads Creator] Installation failed:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    Write-Host ""
    Write-Host "If this PC has no winget, install Python 3.11+ manually and run install.bat again."
    exit 1
}
