"""
Загрузка данных из внешних источников.
"""
import httpx
from loguru import logger
from app.config import settings


async def fetch_metar(station: str, hours: int = 24) -> list:
    url = settings.NOAA_API_URL
    params = {"ids": station, "format": "json", "hours": hours}
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()
    logger.info(f"Получено {len(data)} METAR для {station}")
    return data


def parse_groz_from_metar(metar_list: list) -> list:
    groz_events = []
    for metar in metar_list:
        raw = metar.get("rawOb", "")
        if "TS" in raw:
            groz_events.append({
                "time": metar.get("reportTime"),
                "station": metar.get("icaoId"),
                "raw": raw,
            })
    return groz_events
