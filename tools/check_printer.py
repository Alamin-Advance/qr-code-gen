# tools/check_printer.py
import socket

PRINTER_IP = "192.168.2.169"   # change if printer IP changes
PRINTER_PORT = 9100            # standard ESC/POS raw printing port

def check_printer(ip, port, timeout=5):
    try:
        s = socket.create_connection((ip, port), timeout=timeout)
        s.close()
        return True
    except Exception as e:
        print("Printer not reachable:", e)
        return False

if __name__ == "__main__":
    if check_printer(PRINTER_IP, PRINTER_PORT):
        print("Printer is online and accepting connections.")
    else:
        print("Printer is offline or not reachable.")