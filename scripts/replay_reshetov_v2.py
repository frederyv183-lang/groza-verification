"""
Модель reshetov_v2 — Решетов с мягким порогом.

Аппроксимация графика (рис. 2.2 ВКР) со сдвигом вправо на 5°C:
  line_dH = 7.0 - 0.25 * (T500 + 40)
Это позволяет захватить больше гроз, но и больше ложных.

Запуск:
    python -m scripts.replay_reshetov_v2
"""
from loguru import logger
from sqlalchemy import select

from src.data.storage import Forecast, Sounding, get_session, init_db

MODEL = "reshetov_v2"
STATION = "UUDD"


def reshetov_predict(t500, z500, z850):
    if any(v is None for v in [t500, z500, z850]):
        return None
    if t500 > -12:
        return False
    H_vg_km = z500 / 1000.0
    dH_km = H_vg_km - 1.5
    if dH_km < 0:
        dH_km = 0.0
    # Мягкая линия
    line_dH = 7.0 - 0.25 * (t500 + 40) + 1.0
    return dH_km > line_dH


def main():
    logger.info(f"Запись прогнозов {MODEL}")
    init_db()
    session = get_session()

    rows = session.execute(
        select(Sounding.datetime, Sounding.T_500,
               Sounding.Z_500, Sounding.Z_850).where(
            Sounding.station == STATION)
    ).all()

    session.query(Forecast).filter(
        Forecast.station == STATION, Forecast.model_name == MODEL,
    ).delete()
    session.commit()

    n = 0
    for dt, t500, z500, z850 in rows:
        pred = reshetov_predict(t500, z500, z850)
        if pred is None:
            continue
        session.add(Forecast(
            station=STATION, datetime=dt, model_name=MODEL,
            lead_time_hours=12, predicts_groz=bool(pred),
            value=float(t500) if t500 is not None else None,
        ))
        n += int(pred)

    session.commit()
    session.close()
    logger.info(f"✅ {MODEL}: {len(rows)} прогнозов, гроз: {n}")


if __name__ == "__main__":
    main()
