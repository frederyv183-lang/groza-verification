"""
API метрик верификации + in-memory кэш.
"""
import time
from datetime import date

import numpy as np
import pandas as pd
from fastapi import APIRouter, Query
from loguru import logger
from sqlalchemy import select

from src.data.storage import Fact, Forecast, get_session

router = APIRouter()

# === Кэш ===
_CACHE = {"models": None, "ts": 0}
CACHE_TTL = 300  # 5 минут


def _cm(y_true, y_pred):
    y_true = np.asarray(y_true).astype(int)
    y_pred = np.asarray(y_pred).astype(int)
    h = int(np.sum((y_true == 1) & (y_pred == 1)))
    m = int(np.sum((y_true == 1) & (y_pred == 0)))
    f = int(np.sum((y_true == 0) & (y_pred == 1)))
    c = int(np.sum((y_true == 0) & (y_pred == 0)))
    return h, m, f, c


def _metrics(cm):
    h, m, f, c = cm
    pod = h / (h + m) if (h + m) else 0.0
    far = f / (h + f) if (h + f) else 0.0
    csi = h / (h + m + f) if (h + m + f) else 0.0
    pofd = f / (f + c) if (f + c) else 0.0
    return {"POD": round(pod, 4), "FAR": round(far, 4),
            "CSI": round(csi, 4), "HK": round(pod - pofd, 4)}


def _load(session, station, model, start, end):
    fc = pd.read_sql(
        select(Forecast.datetime, Forecast.predicts_groz, Forecast.value).where(
            Forecast.station == station,
            Forecast.model_name == model,
            Forecast.datetime >= str(start),
            Forecast.datetime <= str(end) + " 23:59:59",
        ),
        session.bind,
    )
    if fc.empty:
        return fc
    fc["date"] = pd.to_datetime(fc["datetime"]).dt.date
    facts = pd.read_sql(
        select(Fact.datetime).where(Fact.station == station, Fact.has_groz == True),
        session.bind,
    )
    groz_days = set(pd.to_datetime(facts["datetime"]).dt.date.unique())
    fc["y_true"] = fc["date"].isin(groz_days).astype(int)
    fc["y_pred"] = fc["predicts_groz"].astype(int)
    return fc


@router.get("/calculate")
async def calculate_metrics(
    station: str = Query("UUDD"),
    model: str = Query("k_index_v1"),
    start_date: str = Query("2020-01-01"),
    end_date: str = Query("2026-12-31"),
):
    session = get_session()
    try:
        df = _load(session, station, model,
                   date.fromisoformat(start_date), date.fromisoformat(end_date))
        if df.empty:
            return {"station": station, "model": model,
                    "period": {"start": start_date, "end": end_date},
                    "metrics": {"POD": None, "FAR": None, "CSI": None, "HK": None},
                    "confusion": {"H": 0, "M": 0, "F": 0, "C": 0},
                    "n_forecasts": 0, "n_forecasts_groz": 0, "n_facts_groz": 0}
        cm = _cm(df["y_true"], df["y_pred"])
        m = _metrics(cm)
        return {
            "station": station, "model": model,
            "period": {"start": start_date, "end": end_date},
            "metrics": m,
            "confusion": {"H": cm[0], "M": cm[1], "F": cm[2], "C": cm[3]},
            "n_forecasts": int(len(df)),
            "n_forecasts_groz": int(df["y_pred"].sum()),
            "n_facts_groz": int(df["y_true"].sum()),
        }
    finally:
        session.close()


@router.get("/confusion-matrix")
async def confusion_matrix(
    station: str = "UUDD", model: str = "k_index_v1", year: int = 2024,
):
    session = get_session()
    try:
        df = _load(session, station, model, date(year, 1, 1), date(year, 12, 31))
        if df.empty:
            return {"station": station, "model": model, "year": year,
                    "matrix": {"hits": 0, "misses": 0,
                               "false_alarms": 0, "correct_negatives": 0}}
        cm = _cm(df["y_true"], df["y_pred"])
        return {
            "station": station, "model": model, "year": year,
            "matrix": {"hits": cm[0], "misses": cm[1],
                       "false_alarms": cm[2], "correct_negatives": cm[3]},
        }
    finally:
        session.close()


@router.get("/models")
async def list_models_with_metrics():
    """Список моделей + метрики (с кэшем на 5 минут)."""
    now = time.time()
    if _CACHE["models"] and (now - _CACHE["ts"]) < CACHE_TTL:
        logger.info(f"Кэш: {len(_CACHE['models'])} моделей")
        return {"models": _CACHE["models"], "cached": True}

    logger.info("Кэш устарел, пересчитываю метрики...")
    t0 = time.time()

    session = get_session()
    try:
        models = pd.read_sql(
            select(Forecast.model_name).distinct(), session.bind,
        )["model_name"].tolist()

        facts = pd.read_sql(
            select(Fact.datetime).where(
                Fact.station == "UUDD", Fact.has_groz == True),
            session.bind,
        )
        groz_days = set(pd.to_datetime(facts["datetime"]).dt.date.unique())

        result = []
        for m in models:
            fc = pd.read_sql(
                select(Forecast.datetime, Forecast.predicts_groz).where(
                    Forecast.station == "UUDD",
                    Forecast.model_name == m,
                ),
                session.bind,
            )
            if fc.empty:
                continue
            fc["date"] = pd.to_datetime(fc["datetime"]).dt.date
            y_true = fc["date"].isin(groz_days).astype(int).values
            y_pred = fc["predicts_groz"].astype(int).values
            cm = _cm(y_true, y_pred)
            result.append({
                "model": m, "metrics": _metrics(cm),
                "n_forecasts": int(len(fc)),
                "n_forecasts_groz": int(y_pred.sum()),
            })

        _CACHE["models"] = result
        _CACHE["ts"] = now
        elapsed = time.time() - t0
        logger.info(f"Пересчитано за {elapsed:.2f} сек")
        return {"models": result, "cached": False, "elapsed_sec": round(elapsed, 2)}
    finally:
        session.close()
