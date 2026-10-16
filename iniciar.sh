#!/usr/bin/env bash
# Tutor Modelista - inicia la plataforma (Mac/Linux). La primera vez instala todo solo.
cd "$(dirname "$0")" || exit 1
if [ ! -d venv ]; then
  echo "Preparando la plataforma por primera vez, tarda unos minutos..."
  python3 -m venv venv || { echo "Falta Python 3 (https://www.python.org/downloads/)"; exit 1; }
  . venv/bin/activate
  pip install --upgrade pip && pip install -r requirements.txt
else
  . venv/bin/activate
fi
echo "Abre en el navegador: http://localhost:8501  (otros equipos: http://IP-DE-ESTE-EQUIPO:8501)"
exec streamlit run app.py --server.address 0.0.0.0 --server.port 8501 --server.headless true --browser.gatherUsageStats false
