@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\pythonw.exe" (
    echo El entorno del prototipo no esta preparado.
    echo Abra esta carpeta en VS Code y siga las instrucciones de README.md.
    pause
    exit /b 1
)

start "Millonario educativo" ".venv\Scripts\pythonw.exe" "main.py"
exit /b 0
