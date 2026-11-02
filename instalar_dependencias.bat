@echo off
setlocal
title Instalar dependencias Piano MIDI Studio (Python 3.11)
set "BASE_PY=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
set "PYTHON=%~dp0.venv311\Scripts\python.exe"

if not exist "%PYTHON%" (
    if not exist "%BASE_PY%" (
        echo No se encontro Python 3.11 en %BASE_PY%.
        pause
        exit /b 1
    )
    "%BASE_PY%" -m venv "%~dp0.venv311"
    if errorlevel 1 exit /b 1
)

"%PYTHON%" -m pip install torch==2.6.0 torchaudio==2.6.0 --index-url https://download.pytorch.org/whl/cu124
if errorlevel 1 exit /b 1

"%PYTHON%" -m pip install -r "%~dp0requirements-full-song.txt"
if errorlevel 1 exit /b 1

"%PYTHON%" -m pip install --no-deps transkun==2.0.1
if errorlevel 1 exit /b 1

echo Dependencias instaladas en .venv311.
pause
