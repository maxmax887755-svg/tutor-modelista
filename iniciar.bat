@echo off
REM Tutor Modelista - doble clic para iniciar (Windows). La primera vez instala todo solo.
cd /d "%~dp0"
where python >nul 2>nul
if errorlevel 1 (
  echo No encuentro Python. Instalalo desde https://www.python.org/downloads/ marcando "Add Python to PATH" y vuelve a abrir este archivo.
  pause
  exit /b 1
)
if not exist venv (
  echo Preparando la plataforma por primera vez, tarda unos minutos...
  python -m venv venv
  call venv\Scripts\activate
  python -m pip install --upgrade pip
  pip install -r requirements.txt
) else (
  call venv\Scripts\activate
)
echo.
echo Abre en el navegador:  http://localhost:8501
echo Para que entren desde otros equipos de la escuela usa la direccion de ESTE equipo, por ejemplo http://192.168.1.50:8501
echo (no cierres esta ventana mientras la uses)
echo.
streamlit run app.py --server.address 0.0.0.0 --server.port 8501 --server.headless true --browser.gatherUsageStats false
pause
