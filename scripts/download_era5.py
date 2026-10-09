"""
Скачивание ERA5 (pressure levels) → data/raw/era5/.
Запуск: python -m scripts.download_era5
"""
import time
from pathlib import Path

import cdsapi
from loguru import logger

AREA = [56, 37, 55, 38]
PRESSURE_LEVELS = ["850", "700", "500"]
VARIABLES = ["temperature", "specific_humidity", "geopotential"]
YEARS = list(range(2020, 2027))
TIMES = ["00:00", "12:00"]
OUT_DIR = Path("data/raw/era5")


def is_valid(path):
    return path.exists() and path.stat().st_size > 100_000


def download_year(client, year):
    out = OUT_DIR / f"era5_UUDD_{year}.nc"
    if is_valid(out):
        logger.info(f"[{year}] Уже скачан")
        return out
    if year == 2026:
        months = [f"{m:02d}" for m in range(1, 11)]
    else:
        months = [f"{m:02d}" for m in range(1, 13)]
    days = [f"{d:02d}" for d in range(1, 32)]
    logger.info(f"[{year}] Отправляю запрос...")
    try:
        client.retrieve(
            "reanalysis-era5-pressure-levels",
            {
                "product_type": ["reanalysis"],
                "variable": VARIABLES,
                "year": [str(year)],
                "month": months, "day": days, "time": TIMES,
                "pressure_level": PRESSURE_LEVELS,
                "data_format": "netcdf", "download_format": "unarchived",
                "area": AREA,
            },
            str(out),
        )
        logger.info(f"[{year}] ✅ {out.name} ({out.stat().st_size // 1024} КБ)")
        return out
    except Exception as e:
        logger.error(f"[{year}] ❌ {e}")
        return None


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    client = cdsapi.Client()
    for year in YEARS:
        download_year(client, year)
        time.sleep(2)


if __name__ == "__main__":
    main()
