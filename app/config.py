"""
Конфигурация приложения.
"""
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "GrozVerification"
    APP_HOST: str = "127.0.0.1"
    APP_PORT: int = 5000
    DEBUG: bool = True

    DATABASE_URL: str = "sqlite:///./data/processed/groz.db"

    DATA_RAW_DIR: Path = Path("./data/raw")
    DATA_PROCESSED_DIR: Path = Path("./data/processed")
    STATION_ICAO: str = "UUDD"
    STATION_NAME: str = "Домодедово"

    ARCHIVE_START_YEAR: int = 2020
    ARCHIVE_END_YEAR: int = 2024

    NOAA_API_URL: str = "https://www.aviationweather.gov/api/data/metar"
    OPENMETEO_API_URL: str = "https://api.open-meteo.com/v1/forecast"


settings = Settings()
