"""
API аналитики: метрики моделей по годам (ускоренная версия).
"""
import time
from collections import defaultdict

import numpy as np
import pandas as pd
from fastapi import APIRouter, Query
from loguru import logger
from sqlalchemy import select, text

from src.data.storage import Fact, Forecast, get_session
from src.models.labels import label

router = APIRouter()
YEARS = list(range(2020, 2027))

# Кэш на 30 минут
_CACHE = {
    "by_year": {"data": None, "ts": 0},
    "matrices": {},
}
CACHE_TTL = 1800  # 30 минут


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


def _load_data_optimized(session, station="UUDD"):
    """
    ОДИН SQL-запрос — сразу факты + прогнозы, сгруппированные по дням.
    Быстрее, чем N запросов.
    """
    # Получаем список грозовых дней
    facts = pd.read_sql(
        text("SELECT DISTINCT DATE(datetime) as d FROM facts "
             "WHERE station = :s AND has_groz = 1"),
        session.bind,
        params={"s": station},
    )
    groz_days = set(pd.to_datetime(facts["d"]).dt.date)

    # Все прогнозы одним запросом
    fc = pd.read_sql(
        text("SELECT model_name, datetime, predicts_groz FROM forecasts "
             "WHERE station = :s"),
        session.bind,
        params={"s": station},
    )
    fc["date"] = pd.to_datetime(fc["datetime"]).dt.date
    fc["year"] = pd.to_datetime(fc["datetime"]).dt.year
    fc["y_true"] = fc["date"].isin(groz_days).astype(int)
    fc["y_pred"] = fc["predicts_groz"].astype(int)
    return fc


@router.get("/by-year")
async def metrics_by_year(station: str = Query("UUDD")):
    """Метрики каждой модели по каждому году (кэш 30 мин)."""
    global _CACHE
    now = time.time()

    if _CACHE["by_year"]["data"] and (now - _CACHE["by_year"]["ts"]) < CACHE_TTL:
        logger.info("by-year: кэш")
        return _CACHE["by_year"]["data"]

    logger.info("by-year: пересчёт (оптимизированный)...")
    t0 = time.time()
    session = get_session()
    try:
        fc = _load_data_optimized(session, station)
        models = sorted(fc["model_name"].unique().tolist())

        result = {}
        for model in models:
            sub = fc[fc["model_name"] == model]
            if sub.empty:
                continue
            per_year = {}
            for year in YEARS:
                y = sub[sub["year"] == year]
                if y.empty:
                    continue
                cm = _cm(y["y_true"], y["y_pred"])
                m = _metrics(cm)
                m.update({"H": cm[0], "M": cm[1], "F": cm[2],
                          "C": cm[3], "N": len(y)})
                per_year[str(year)] = m
            result[model] = per_year

        # Сортировка по средней CSI
        def avg_csi(m):
            vals = [v["CSI"] for v in result[m].values()]
            return sum(vals) / len(vals) if vals else 0

        sorted_models = sorted(result.keys(), key=avg_csi, reverse=True)

        payload = {
            "station": station,
            "years": YEARS,
            "models": sorted_models,
            "labels": {m: label(m) for m in sorted_models},
            "data": result,
        }
        _CACHE["by_year"]["data"] = payload
        _CACHE["by_year"]["ts"] = now
        logger.info(f"by-year: пересчитано за {time.time()-t0:.2f} сек")
        return payload
    finally:
        session.close()


@router.get("/matrices")
async def matrices_by_year(
    station: str = Query("UUDD"),
    model: str = Query("k_index_v1"),
):
    """Матрицы ошибок для модели по всем годам (кэш 30 мин)."""
    global _CACHE
    now = time.time()
    key = f"{station}:{model}"

    if key in _CACHE["matrices"]:
        entry = _CACHE["matrices"][key]
        if (now - entry["ts"]) < CACHE_TTL:
            return entry["data"]

    session = get_session()
    try:
        facts = pd.read_sql(
            text("SELECT DISTINCT DATE(datetime) as d FROM facts "
                 "WHERE station = :s AND has_groz = 1"),
            session.bind, params={"s": station},
        )
        groz_days = set(pd.to_datetime(facts["d"]).dt.date)

        fc = pd.read_sql(
            text("SELECT datetime, predicts_groz FROM forecasts "
                 "WHERE station = :s AND model_name = :m"),
            session.bind, params={"s": station, "m": model},
        )
        if fc.empty:
            return {"station": station, "model": model, "years": []}

        fc["date"] = pd.to_datetime(fc["datetime"]).dt.date
        fc["year"] = pd.to_datetime(fc["datetime"]).dt.year
        fc["y_true"] = fc["date"].isin(groz_days).astype(int)
        fc["y_pred"] = fc["predicts_groz"].astype(int)

        years_data = []
        for year in YEARS:
            sub = fc[fc["year"] == year]
            if sub.empty:
                continue
            cm = _cm(sub["y_true"], sub["y_pred"])
            m = _metrics(cm)
            years_data.append({
                "year": int(year),
                "hits": cm[0], "misses": cm[1],
                "false_alarms": cm[2], "correct_negatives": cm[3],
                "n": len(sub),
                "POD": m["POD"], "FAR": m["FAR"],
                "CSI": m["CSI"], "HK": m["HK"],
            })

        payload = {
            "station": station, "model": model,
            "model_label": label(model),
            "years": years_data,
        }
        _CACHE["matrices"][key] = {"data": payload, "ts": now}
        return payload
    finally:
        session.close()


@router.get("/cache/clear")
async def clear_cache():
    global _CACHE
    _CACHE = {"by_year": {"data": None, "ts": 0}, "matrices": {}}
    logger.info("Кэш аналитики сброшен")
    return {"status": "ok"}


@router.get("/status")
async def cache_status():
    now = time.time()
    age = round(now - _CACHE["by_year"]["ts"], 1) if _CACHE["by_year"]["ts"] else None
    return {
        "by_year_age_sec": age,
        "by_year_cached": _CACHE["by_year"]["data"] is not None,
        "matrices_keys": list(_CACHE["matrices"].keys()),
        "ttl_sec": CACHE_TTL,
    }
