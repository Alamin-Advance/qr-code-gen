# app/config.py
# Central place for simple settings

from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DB_URL: str = "sqlite:///./app.db"      # a file app.db in project root
    ISSUER_NAME: str = "MyCompanyGate"      # used in QR payloads

settings = Settings()
