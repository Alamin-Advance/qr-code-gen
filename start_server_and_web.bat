@echo off
cd /d F:\qr-code-gen

REM start the server in a new window using the venv's python
start "QR API" cmd /c ".qrenv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

REM wait a moment for the server, then open the web UI
timeout /t 2 >nul
start "" "http://127.0.0.1:8000/web/"