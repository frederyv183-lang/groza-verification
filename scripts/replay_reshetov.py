"""
Модель reshetov_v1 — метод Г.Д. Решетова.

Аппроксимация графика (рис. 2.2 ВКР):
  Линия раздела:  ΔH = 9 - 0.3 * (Tв - (-40))
                  т.е. ΔH = 9 - 0.3 * (Tв + 40)
  Если ΔH_факт > ΔH_линия → гроза ожидается

Для ERA5:
  Hв ≈ Z_500 (высота 500 гПа, ~5.5 км)
  Tв = T_500 (°C)
  ΔH = толщина слоя с T<0°C — упрощённо (Z_500 - Z_850)/1000 при T_500 < 0

Запуск:
    python -m scripts.replay_reshetov
"""
import pandas as pd
from loguru import logger
from sqlalchemy import select

from src.data.storage import Forecast, Sounding, get_session, init_db

MODEL = "reshetov_v1"
STATION = "UUDD"


def reshetov_predict(t500, z500, z850, t850):
    """
    Возвращает True/False/None.
    """
    if any(v is None for v in [t500, z500, z850, t850]):
        return None

    # Упрощение: если T500 > -12, Cb не развивается
    if t500 > -12:
        return False

    # ΔH — толщина слоя с отрицательной T (грубо: от уровня T=0°C до Z500)
    # Аппроксимация: ΔH ≈ Z500/1000 - 1.5 (1.5 км — уровень 0°C зимой/летом)
    H_vg_km = z500 / 1000.0
    dH_km = H_vg_km - 1.5
    if dH_km < 0:
        dH_km = 0.0

    # Линия раздела графика
    line_dH = 9.0 - 0.3 * (t500 + 40)

    return dH_km > line_dH


def main():
    logger.info(f"Запись прогнозов {MODEL}")
    init_db()
    session = get_session()

    rows = session.execute(
        select(Sounding.datetime, Sounding.T_500, Sounding.T_850,
               Sounding.Z_500, Sounding.Z_850).where(
            Sounding.station == STATION)
    ).all()

    session.query(Forecast).filter(
        Forecast.station == STATION, Forecast.model_name == MODEL,
    ).delete()
    session.commit()

    n_groz = 0
    for dt, t500, t850, z500, z850 in rows:
        pred = reshetov_predict(t500, z500, z850, t850)
        if pred is None:
            continue
        session.add(Forecast(
            station=STATION, datetime=dt, model_name=MODEL,
            lead_time_hours=12, predicts_groz=bool(pred),
            value=float(t500) if t500 is not None else None,
        ))
        n_groz += int(pred)

    session.commit()
    session.close()
    logger.info(f"✅ {MODEL}: {len(rows)} прогнозов, гроз: {n_groz}")


if __name__ == "__main__":
    main()
