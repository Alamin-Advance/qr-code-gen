import threading, webbrowser
import uvicorn

URL = "http://127.0.0.1:8000/web/"

def open_browser():
    try:
        webbrowser.open(URL)
    except Exception:
        pass

if __name__ == "__main__":
    # open the browser shortly after the server starts
    threading.Timer(1.0, open_browser).start()
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)