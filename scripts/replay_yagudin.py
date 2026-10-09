"""
Модель yagudin_v1 — метод Р.А. Ягудина.

Упрощённая реализация 3 графиков (рис. 2.3 ВКР):
  График а: ΔT'(700) vs Σq(850-700)
  График б: ΔT'(500) vs Σ(T-Td)(850)
  График в: (T-Td)700 vs ΔT'500

Мы используем упрощённые линейные пороги:
  a) ΔT'700 > 5 - 0.2*Σq(850-700)  → в зоне гроз
  б) ΔT'500 > -3 + 0.05*Σ(T-Td)(850) → в зоне гроз
  в) (T-Td)700 > 3 + 0.3*(ΔT'500 - 2) → в зоне гроз

Гроза, если ВСЕ три условия выполнены.

Запуск:
    python -m scripts.replay_yagudin
"""
import pandas as pd
from loguru import logger
from sqlalchemy import select

from src.data.storage import Forecast, Sounding, get_session, init_db

MODEL = "yagudin_v1"
STATION = "UUDD"


def yagudin_predict(t700, td700, t500, td500, t850, td850):
    """Возвращает True/False/None."""
    if any(v is None for v in [t700, td700, t500, td500, t850, td850]):
        return None

    # Приблизительные предикторы Ягудина:
    dT700 = t700 - t500  # перепад в слое 700–500
    dT500 = t500 - t850  # грубая оценка индекса неустойчивости на 500

    # Σq(850–700) — упрощённо через разность Td
    sum_q = (td850 + td700) / 2

    # Σ(T-Td)(850)
    d850 = t850 - td850

    # Условие а
    cond_a = dT700 > (5.0 - 0.2 * sum_q)
    # Условие б
    cond_b = dT500 > (-3.0 + 0.05 * d850)
    # Условие в
    cond_v = (t700 - td700) > (3.0 + 0.3 * (dT500 - 2))

    # Все три условия должны выполняться
    return bool(cond_a and cond_b and cond_v)


def main():
    logger.info(f"Запись прогнозов {MODEL}")
    init_db()
    session = get_session()

    rows = session.execute(
        select(Sounding.datetime, Sounding.T_700, Sounding.Td_700,
               Sounding.T_500, Sounding.Td_500,
               Sounding.T_850, Sounding.Td_850).where(
            Sounding.station == STATION)
    ).all()

    session.query(Forecast).filter(
        Forecast.station == STATION, Forecast.model_name == MODEL,
    ).delete()
    session.commit()

    n_groz = 0
    for dt, t700, td700, t500, td500, t850, td850 in rows:
        pred = yagudin_predict(t700, td700, t500, td500, t850, td850)
        if pred is None:
            continue
        session.add(Forecast(
            station=STATION, datetime=dt, model_name=MODEL,
            lead_time_hours=12, predicts_groz=bool(pred),
            value=float(t850) if t850 is not None else None,
        ))
        n_groz += int(pred)

    session.commit()
    session.close()
    logger.info(f"✅ {MODEL}: {len(rows)} прогнозов, гроз: {n_groz}")


if __name__ == "__main__":
    main()
