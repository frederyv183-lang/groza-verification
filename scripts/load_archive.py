"""
Загрузка архива METAR.
Запуск: python -m scripts.load_archive
"""
import asyncio
from datetime import datetime, timedelta
from loguru import logger

from src.data.loader import fetch_metar, parse_groz_from_metar
from src.data.storage import init_db
from app.config import settings


async def load_year(year: int, station: str) -> int:
    total = 0
    for month in range(1, 13):
        start = datetime(year, month, 1)
        end = (start + timedelta(days=32)).replace(day=1)
        hours = int((end - start).total_seconds() // 3600)
        logger.info(f"Загрузка {station} за {year}-{month:02d}")
        try:
            metars = await fetch_metar(station, hours=hours)
            groz = parse_groz_from_metar(metars)
            total += len(groz)
        except Exception as e:
            logger.error(f"Ошибка {year}-{month:02d}: {e}")
    return total


async def main():
    init_db()
    station = settings.STATION_ICAO
    grand_total = 0
    for year in range(settings.ARCHIVE_START_YEAR, settings.ARCHIVE_END_YEAR + 1):
        n = await load_year(year, station)
        grand_total += n
        logger.info(f"За {year}: {n} случаев грозы")
    logger.info(f"Всего: {grand_total}")


if __name__ == "__main__":
    asyncio.run(main())
