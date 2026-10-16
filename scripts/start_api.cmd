@echo off
setlocal
cd /d "%~dp0.."

if not exist ".venv\Scripts\python.exe" (
  echo [ERROR] Backend virtual environment not found.
  echo Run these commands from the backend folder first:
  echo   py -3.13 -m venv .venv
  echo   .venv\Scripts\python.exe -m pip install -r requirements.txt
  exit /b 1
)

if not defined CONDA_PREFIX (
  echo [ERROR] Conda environment is not active.
  echo Open Anaconda Prompt, run "conda activate offgridders_env", then run this script again.
  exit /b 1
)

if not exist "%CONDA_PREFIX%\python.exe" (
  echo [ERROR] Python was not found under the active Conda environment:
  echo   %CONDA_PREFIX%
  exit /b 1
)

set "OFFGRIDDERS_ROOT=%CD%\engine\offgridders"
set "OFFGRIDDERS_PYTHON=%CONDA_PREFIX%\python.exe"
set "PATH=%CONDA_PREFIX%\Library\bin;%CONDA_PREFIX%\Scripts;%PATH%"

if not defined DESANYALA_CORS_ORIGINS set "DESANYALA_CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000,http://localhost:5500,http://127.0.0.1:5500"

if not exist "%OFFGRIDDERS_ROOT%\Offgridders.py" (
  echo [ERROR] Offgridders.py not found at:
  echo   %OFFGRIDDERS_ROOT%
  echo Check that the Offgridders source has been imported into backend\engine\offgridders.
  exit /b 1
)

if not exist "%OFFGRIDDERS_ROOT%\src" (
  echo [ERROR] Offgridders src folder not found at:
  echo   %OFFGRIDDERS_ROOT%\src
  exit /b 1
)

echo Starting DesaNyala API...
echo API: http://127.0.0.1:8000
echo Docs: http://127.0.0.1:8000/docs
echo CORS: %DESANYALA_CORS_ORIGINS%
.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
