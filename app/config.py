# app/config.py
# Central place for simple settings
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DB_URL: str = "sqlite:///./app.db"      # DB file in project root
    ISSUER_NAME: str = "MyCompanyGate"

settings = Settings()

# Your local timezone for display/printing
TIMEZONE = "Europe/Istanbul"