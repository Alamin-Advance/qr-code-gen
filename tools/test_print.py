from escpos.printer import Network

# Change to your printer's IP
printer = Network("192.168.2.169", port=9100)

printer.text("Hello from Gate Entry System!\n")
printer.text("This is a QR test print.\n")
printer.cut()