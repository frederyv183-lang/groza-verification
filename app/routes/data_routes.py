"""
API-эндпоинты для работы с данными (факты, прогнозы).
"""
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query
from loguru import logger
from sqlalchemy import func, select

from src.data.storage import Fact, get_session

router = APIRouter()


@router.get("/stations")
async def get_stations():
    """Список доступных станций."""
    return {
        "stations": [
            {"icao": "UUDD", "name": "Домодедово"},
            {"icao": "UUEE", "name": "Шереметьево"},
            {"icao": "UUWW", "name": "Внуково"},
        ]
    }


@router.get("/facts/{station}")
async def get_facts(
    station: str,
    year: int | None = Query(None, description="Фильтр по году"),
    month: int | None = Query(None, ge=1, le=12, description="Фильтр по месяцу"),
    only_groz: bool = Query(False, description="Только грозовые сводки"),
    limit: int = Query(1000, ge=1, le=50000, description="Максимум записей"),
    offset: int = Query(0, ge=0),
):
    """
    Получить фактические METAR-сводки по станции.

    Примеры:
        /api/data/facts/UUDD?year=2024
        /api/data/facts/UUDD?year=2024&month=7&only_groz=true
    """
    station = station.upper()
    logger.info(f"Запрос фактов: station={station}, year={year}, month={month}, only_groz={only_groz}")

    session = get_session()
    try:
        # Базовый запрос
        stmt = select(Fact).where(Fact.station == station)

        # Фильтры
        if year is not None:
            stmt = stmt.where(func.strftime("%Y", Fact.datetime) == str(year))
        if month is not None:
            stmt = stmt.where(func.strftime("%m", Fact.datetime) == f"{month:02d}")
        if only_groz:
            stmt = stmt.where(Fact.has_groz.is_(True))

        # Общее число (без limit)
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = session.execute(count_stmt).scalar() or 0

        # Сортировка и пагинация
        stmt = stmt.order_by(Fact.datetime).limit(limit).offset(offset)
        rows = session.execute(stmt).scalars().all()

        # Формируем ответ
        items = [
            {
                "id": r.id,
                "station": r.station,
                "datetime": r.datetime.isoformat() if r.datetime else None,
                "has_groz": bool(r.has_groz),
                "raw_metar": r.raw_metar,
            }
            for r in rows
        ]

        # Дополнительная статистика (если запросили без only_groz)
        groz_count = None
        if not only_groz:
            groz_stmt = select(func.count()).where(
                Fact.station == station,
                Fact.has_groz.is_(True),
            )
            if year is not None:
                groz_stmt = groz_stmt.where(func.strftime("%Y", Fact.datetime) == str(year))
            if month is not None:
                groz_stmt = groz_stmt.where(func.strftime("%m", Fact.datetime) == f"{month:02d}")
            groz_count = session.execute(groz_stmt).scalar() or 0

        return {
            "station": station,
            "filters": {
                "year": year,
                "month": month,
                "only_groz": only_groz,
            },
            "total": total,
            "returned": len(items),
            "offset": offset,
            "groz_count": groz_count,
            "items": items,
        }
    finally:
        session.close()


@router.get("/stats/{station}")
async def get_stats(station: str):
    """
    Сводная статистика по станции за весь архив.
    """
    station = station.upper()
    session = get_session()
    try:
        total = session.execute(
            select(func.count()).where(Fact.station == station)
        ).scalar() or 0

        groz = session.execute(
            select(func.count()).where(Fact.station == station, Fact.has_groz.is_(True))
        ).scalar() or 0

        days_with_groz = session.execute(
            select(func.count(func.distinct(func.date(Fact.datetime)))).where(
                Fact.station == station,
                Fact.has_groz.is_(True),
            )
        ).scalar() or 0

        return {
            "station": station,
            "total_reports": total,
            "groz_reports": groz,
            "groz_days": days_with_groz,
            "frequency_pct": round(100 * groz / total, 2) if total else 0,
        }
    finally:
        session.close()


@router.get("/forecasts/{station}")
async def get_forecasts(station: str, model: str = "all", year: int = 2024):
    """Прогнозы по станции за год (заглушка — заполним позже)."""
    logger.info(f"Запрос прогнозов: {station}, {model}, {year}")
    return {"station": station.upper(), "model": model, "year": year, "forecasts": []}