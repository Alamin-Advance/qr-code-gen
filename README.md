#QR Code Gate Entry System (FastAPI + Python)

A **fast gate entry system** built with **Python & FastAPI** that issues, verifies, and prints QR codes for access control.  
Designed to replace the older PHP + C++ version, this solution reduces printing time from ~5–10 seconds to just **2 seconds**.

---

## Features
- ✅ Generate unique QR codes with expiration time and scan limits  
- ✅ Print QR codes instantly to a network thermal printer (ESC/POS)  
- ✅ Verify QR codes via camera scanner (OpenCV + FastAPI backend)  
- ✅ Turkish characters (`ş, ğ, ü, ö, ı`) supported  
- ✅ Web interface for easy QR issuing  
- ✅ REST API (Swagger UI at `/docs`) for programmatic access  
- ✅ Works on Windows (PowerShell + VS Code)  

---

## 🛠 Tech Stack
- **Backend:** [FastAPI](https://fastapi.tiangolo.com/)  
- **Database:** SQLite (default), easily swappable with PostgreSQL  
- **Frontend:** Static HTML/JS served from FastAPI (`/web/`)  
- **Printing:** [python-escpos](https://python-escpos.readthedocs.io/) for network thermal printers  
- **Scanning:** OpenCV + QRCodeDetector  
- **Environment:** Python 3.11+ with `venv`  

## 📂 Project Structure
qr-code-gen/
│── app/
│ ├── main.py # FastAPI app
│ ├── models.py # Database models (Users, Tokens, Logs)
│ ├── db.py # Database setup
│ ├── printer.py # ESC/POS printing
│ └── config.py # Settings (DB path, Issuer, Timezone)
│── gate_scanner/
│ └── gate_scanner.py # Camera-based QR verification
│── web/
│ ├── index.html # Web interface
│ ├── style.css
│ └── script.js
│── start_server_and_web.bat # One-click server + browser launcher
│── requirements.txt # Dependencies
│── README.md # Project docs



## ⚙️ Installation

### 1. Clone the repo

git clone https://github.com/<your-user>/qr-code-gen.git
cd qr-code-gen
2. Create & activate virtual environment

python -m venv .qrenv
.\.qrenv\Scripts\activate   # Windows
3. Install dependencies

pip install -r requirements.txt
4. Initialize database

python -m app.init_db
▶️ Usage
Start server (manual)

uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
Open http://127.0.0.1:8000/ → Web UI

Swagger API docs available at /docs

Start server (auto browser)
Just double-click:

start_server_and_web.bat
This opens the server and your browser automatically.

🖨 Printing
Works with any ESC/POS network printer (default port 9100).

Configure printer IP in app/printer.py:

PRINTER_IP = "192.x.x.x"
PRINTER_PORT = xxx
Prints QR only for fastest response (~2 seconds).

📷 Scanning
Run the scanner with your webcam:

python gate_scanner/gate_scanner.py
Shows camera feed in a small window.

Verifies QR against the API.

Plays sound + optional voice feedback (“Teşekkürler”).

👥 Team Workflow
Commit & push changes:

git add .
git commit -m "Describe change"
git push
Teammates can git pull to update their copy.

📌 Notes
Default database is SQLite (app.db in project root).
For production, switch to PostgreSQL/MySQL in config.py.
QR images are generated in memory (not saved to disk).
Status is returned in Turkish (Aktif / Pasif).
