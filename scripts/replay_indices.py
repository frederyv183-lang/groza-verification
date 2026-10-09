"""
Модели: fateev_v1, lebedev_v1, bailey_v1 (скорректированные пороги).

Пороги подобраны так, чтобы:
  - fateev_v1: A >= 5 (вместо 0) → меньше ложных
  - lebedev_v1: ΣD <= 20 И НЕ Бейли → меньше ложных
  - bailey_v1: НЕ Бейли → оставляем (это метод отсутствия)

Запуск:
    python -m scripts.replay_indices
"""
from loguru import logger
from sqlalchemy import select

from src.data.storage import Forecast, Sounding, get_session, init_db

STATION = "UUDD"


def main():
    init_db()
    session = get_session()

    rows = session.execute(select(Sounding)).scalars().all()
    logger.info(f"Загружено {len(rows)} звудирований")

    # === fateev_v1 с порогом A >= 5 ===
    session.query(Forecast).filter(
        Forecast.station == STATION, Forecast.model_name == "fateev_v1",
    ).delete()
    n = 0
    for s in rows:
        if s.Fateev_A is None:
            continue
        pred = s.Fateev_A >= 5.0
        session.add(Forecast(
            station=STATION, datetime=s.datetime, model_name="fateev_v1",
            lead_time_hours=12, predicts_groz=bool(pred), value=s.Fateev_A,
        ))
        n += int(pred)
    session.commit()
    logger.info(f"✅ fateev_v1 (A>=5): {len(rows)} прогнозов, гроз: {n}")

    # === lebedev_v1 (строже) ===
    session.query(Forecast).filter(
        Forecast.station == STATION, Forecast.model_name == "lebedev_v1",
    ).delete()
    n = 0
    for s in rows:
        if s.Lebedeva_SD is None or s.Bailey_no_groz is None:
            continue
        pred = (s.Lebedeva_SD <= 20) and (not s.Bailey_no_groz)
        session.add(Forecast(
            station=STATION, datetime=s.datetime, model_name="lebedev_v1",
            lead_time_hours=12, predicts_groz=bool(pred), value=s.Lebedeva_SD,
        ))
        n += int(pred)
    session.commit()
    logger.info(f"✅ lebedev_v1: {len(rows)} прогнозов, гроз: {n}")

    # === bailey_v1 (без изменений) ===
    session.query(Forecast).filter(
        Forecast.station == STATION, Forecast.model_name == "bailey_v1",
    ).delete()
    n = 0
    for s in rows:
        if s.Bailey_no_groz is None:
            continue
        pred = not s.Bailey_no_groz
        session.add(Forecast(
            station=STATION, datetime=s.datetime, model_name="bailey_v1",
            lead_time_hours=12, predicts_groz=bool(pred), value=None,
        ))
        n += int(pred)
    session.commit()
    logger.info(f"✅ bailey_v1: {len(rows)} прогнозов, гроз: {n}")

    # === Удаляем проблемные модели ===
    for bad_model in ["yagudin_v1", "ki_index_v2"]:
        deleted = session.query(Forecast).filter(
            Forecast.station == STATION,
            Forecast.model_name == bad_model,
        ).delete()
        session.commit()
        logger.info(f"🗑  Удалена модель {bad_model}: {deleted} записей")

    session.close()


if __name__ == "__main__":
    main()
