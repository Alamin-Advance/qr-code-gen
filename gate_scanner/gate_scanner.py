# gate_scanner/gate_scanner.py
# Webcam QR scanner using OpenCV with small window and 10s lock + voice on allow.

import cv2
import requests
import time
import winsound  # on non-Windows you can remove or wrap in try/except
import threading
import pyttsx3

API_BASE = "http://127.0.0.1:8000"   # FastAPI server
ISSUER   = "BenimGiriş"           # must match app.main.py
DISPLAY_HOLD_SEC = 10.0              # keep result on screen

# ---------------- TTS (Text-to-Speech) setup ----------------
_tts_engine = pyttsx3.init()  # uses Windows SAPI on Windows
# Try to select a Turkish voice if available
try:
    for v in _tts_engine.getProperty("voices"):
        desc = f"{v.name} | {v.id}".lower()
        if "tr" in desc or "turk" in desc:
            _tts_engine.setProperty("voice", v.id)
            break
except Exception:
    pass
_tts_engine.setProperty("rate", 180)   # speed (150–200 typical)
_tts_engine.setProperty("volume", 1.0) # 0.0–1.0

def speak_async(text: str):
    """Speak without blocking the camera loop."""
    def _run():
        try:
            _tts_engine.say(text)
            _tts_engine.runAndWait()
        except Exception:
            pass
    threading.Thread(target=_run, daemon=True).start()
# ------------------------------------------------------------

def put_text(img, text, y, color=(0, 255, 0)):
    cv2.putText(img, text, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2, cv2.LINE_AA)

def verify(payload: str):
    try:
        r = requests.post(f"{API_BASE}/qr/verify", json={"payload": payload}, timeout=3)
        return r.json(), r.status_code
    except Exception as e:
        return {"ok": False, "reason": f"network_error:{e}"}, 0

def open_camera_small():
    """Open camera with DirectShow (Windows), force ~420x340 resolution."""
    for idx in (0, 1, 2):
        cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)  # CAP_DSHOW is stable on Windows
        if cap.isOpened():
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 420)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 340)
            return cap, idx
        cap.release()
    return None, None

def main():
    cap, idx = open_camera_small()
    if cap is None:
        print("Could not open any camera. Check permissions or try another index.")
        return
    print(f"Camera opened at index {idx}. Press 'q' to quit.")

    window_name = "QR Scanner"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, 420, 340)

    detector = cv2.QRCodeDetector()

    # --- Lock state (freeze result for DISPLAY_HOLD_SEC seconds) ---
    lock_until   = 0.0            # timestamp when we unlock
    locked_text  = ""             # text to display while locked
    locked_color = (0, 200, 0)    # color of the locked message

    while True:
        ok, frame = cap.read()
        if not ok:
            # Show an error in the window (rare)
            put_text(frame if frame is not None else None, "Camera read failed...", 30, (0, 0, 255))
            if frame is not None:
                cv2.imshow(window_name, frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
            continue

        now = time.time()

        if now < lock_until:
            # Still in the hold window: keep showing the last result
            put_text(frame, locked_text, 30, locked_color)
        else:
            # Not locked: detect & decode a new QR
            data, points, _ = detector.detectAndDecode(frame)

            # Draw polygon around detected QR (if any)
            if points is not None:
                pts = points[0].astype(int)
                for i in range(4):
                    p1 = tuple(pts[i]); p2 = tuple(pts[(i + 1) % 4])
                    cv2.line(frame, p1, p2, (255, 255, 0), 2)

            if data:
                data = data.strip()
                # Accept either "ISSUER|token" or just "token"
                if "|" in data:
                    payload = data
                else:
                    payload = f"{ISSUER}|{data}"

                # Verify once and LOCK for DISPLAY_HOLD_SEC seconds
                resp, status = verify(payload)
                if resp.get("ok"):
                    # ----- ALLOWED -----
                    locked_text  = f"ALLOW  user_id={resp.get('user_id')}  scan={resp.get('scan_count')}  status={resp.get('status')}"
                    locked_color = (0, 200, 0)
                    try:
                        winsound.Beep(1200, 150)
                    except Exception:
                        pass
                    # NEW: voice feedback
                    speak_async("Teşekkürler")
                else:
                    # ----- DENIED -----
                    locked_text  = f"DENY  reason={resp.get('reason')}"
                    locked_color = (0, 0, 255)
                    try:
                        winsound.Beep(400, 250)
                    except Exception:
                        pass
                    # If you also want voice for denied, uncomment:
                    # speak_async("Yetkisiz giriş")

                lock_until = now + DISPLAY_HOLD_SEC
                put_text(frame, locked_text, 30, locked_color)
            else:
                # No QR detected and not locked
                put_text(frame, "Show a QR code to the camera…", 30, (200, 200, 200))

        put_text(frame, "Press 'q' to quit", frame.shape[0] - 15, (180, 180, 180))
        cv2.imshow(window_name, frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()