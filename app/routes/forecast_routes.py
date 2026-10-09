"""
API прогнозов.
"""
from fastapi import APIRouter, Query
from sqlalchemy import select
from src.data.storage import Forecast, get_session

router = APIRouter()


@router.get("/models")
async def list_models():
    session = get_session()
    try:
        rows = session.execute(select(Forecast.model_name).distinct()).scalars().all()
        return {"models": [{"id": m, "name": m} for m in rows]}
    finally:
        session.close()


@router.get("/data/{station}")
async def get_forecast_data(
    station: str, model: str = Query("k_index_v1"),
    year: int = Query(2024), limit: int = Query(500, le=5000),
):
    session = get_session()
    try:
        rows = session.execute(
            select(Forecast).where(
                Forecast.station == station.upper(),
                Forecast.model_name == model,
                Forecast.datetime >= f"{year}-01-01",
                Forecast.datetime < f"{year + 1}-01-01",
            ).order_by(Forecast.datetime).limit(limit)
        ).scalars().all()
        return {
            "station": station.upper(), "model": model, "year": year,
            "returned": len(rows),
            "items": [
                {"datetime": r.datetime.isoformat() if r.datetime else None,
                 "predicts_groz": bool(r.predicts_groz), "value": r.value}
                for r in rows
            ],
        }
    finally:
        session.close()
