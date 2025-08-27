# tools/voice_test.py
import pyttsx3

engine = pyttsx3.init()  # uses Windows SAPI on Windows

# Optional: try to select a Turkish voice if available
target_lang = "tr"  # Turkish
selected = False
for v in engine.getProperty("voices"):
    desc = f"{v.name} | {v.id}".lower()
    if "tr" in desc or "turk" in desc:
        engine.setProperty("voice", v.id)
        selected = True
        break

# Optional: tune speaking speed / volume
engine.setProperty("rate", 180)   # 150–200 is typical
engine.setProperty("volume", 1.0) # 0.0–1.0

print("Voice selected:", "Turkish" if selected else "Default system voice")
engine.say("Teşekkürler")
engine.runAndWait()
print("Done.")