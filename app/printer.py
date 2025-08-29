# app/printer.py
# Network ESC/POS printing with native-QR (fast) and bitmap fallback.

from escpos.printer import Network
from typing import Dict
from qrcode import QRCode
from PIL import Image

PRINTER_IP = "192.168.2.169"   # <-- Specify printer's IP
PRINTER_PORT = 9100

def _native_qr(p: Network, payload: str):
    # Native QR is fastest; size 6–10 is typical
    p.qr(payload, size=8, ec="M", model=2, center=True)

def _bitmap_qr(p: Network, payload: str):
    # Slower but universal; prints a generated QR image
    qr = QRCode(border=1, box_size=6)
    qr.add_data(payload)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    if img.mode != "RGB":
        img = img.convert("RGB")
    p.image(img, impl="bitImageColumn")

def print_qr_ticket(payload: str, info: Dict[str, str]) -> bool:
    """
    Print a QR 'ticket' with payload and info fields.
    Returns True if printed, False on error.
    """
    try:
        p = Network(PRINTER_IP, PRINTER_PORT, timeout=5)
        
        #p.charcode("CP1254")   # make sure Turkish letters print correctly (try "CP1254")
        # Header
        p.set(align="center", width=2, height=2, bold=True)
        p.text("Giris QR Kodu\n")
        p.set(align="center", bold=False)
        p.text("-----------------------\n")

        # Try native QR first, fallback to bitmap
        try:
            _native_qr(p, payload)
        except Exception:
            _bitmap_qr(p, payload)

        p.text("\n")

        # Details
        p.set(align="left")
        for k, v in info.items():
            v = "" if v is None else str(v)
            p.text(f"{k}: {v}\n")

        p.text("-----------------------\n")
        p.text("Teknik Departmant Destekli\n")

        p.cut()
        p.close()
        return True
    except Exception as e:
        print("Printer error:", e)
        return False