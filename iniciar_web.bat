@echo off
title Piano MIDI Studio Web (Python 3.11)
echo ======================================================
echo          PIANO MIDI STUDIO - PYTHON 3.11
echo ======================================================
echo Iniciando servidor web...
echo Abriendo tu navegador en http://localhost:8000
echo.

start "" http://localhost:8000
"%~dp0.venv311\Scripts\python.exe" "%~dp0web_app.py"
pause
