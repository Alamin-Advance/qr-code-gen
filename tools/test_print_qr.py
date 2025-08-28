# tools/test_print_qr.py
# Fast test: print a QR ticket to an ESC/POS network printer

import time
from escpos.printer import Network

PRINTER_IP = "192.168.2.169"  # <-- change if your IP changes
PRINTER_PORT = 9100

# The payload you really use in your system (issuer|token)
# For a speed test we make a unique token each run:
payload = f"BenimGiriş|SPEEDTEST-{int(time.time())}"

def print_native_qr():
    """Fastest: use printer's hardware QR command."""
    p = Network(PRINTER_IP, PRINTER_PORT, timeout=5)
    try:
        # Header (centered, big & bold)
        p.set(align="center", width=2, height=2, bold=True)
        p.text("Gate Entry Pass\n")
        p.set(align="center", bold=False)
        p.text("-----------------------\n")

        # Native QR: model=2, error correction M, size 6–10 (try 6 first)
        p.qr(payload, size=8, ec="M", model=2, center=True)
        p.text("\n")

        # Short details
        p.set(align="left")
        p.text(f"Payload: {payload}\n")
        p.text("-----------------------\n")
        p.text("Printed via native QR\n")

        p.cut()
        print("Printed (native QR).")
    finally:
        p.close()

def print_bitmap_qr():
    """Fallback: print a QR image as bitmap if native QR is not supported."""
    from qrcode import QRCode
    from PIL import Image

    # Build QR image
    qr = QRCode(border=1, box_size=6)  # smaller border/box for receipt width
    qr.add_data(payload)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")  # PIL image
    if img.mode != "RGB":
        img = img.convert("RGB")

    p = Network(PRINTER_IP, PRINTER_PORT, timeout=5)
    try:
        p.set(align="center", width=2, height=2, bold=True)
        p.text("Gate Entry Pass\n")
        p.set(align="center", bold=False)
        p.text("-----------------------\n")

        # Print the bitmap QR (a bit slower than native, but works on any ESC/POS)
        p.image(img, impl="bitImageColumn")  # try "bitImageRaster" if needed
        p.text("\n")

        p.set(align="left")
        p.text(f"Payload: {payload}\n")
        p.text("-----------------------\n")
        p.text("Printed via bitmap QR\n")

        p.cut()
        print("Printed (bitmap QR).")
    finally:
        p.close()

if __name__ == "__main__":
    try:
        print_native_qr()
    except Exception as e:
        print("Native QR failed, falling back to bitmap:", e)
        try:
            print_bitmap_qr()
        except Exception as e2:
            print("Bitmap QR also failed:", e2)