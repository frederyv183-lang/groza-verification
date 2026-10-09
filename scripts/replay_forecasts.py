"""
Запись прогнозов K-индекса в таблицу forecasts.
Модель: k_index_v1, порог K >= 22.
Запуск: python -m scripts.replay_forecasts
"""
import pandas as pd
from loguru import logger
from sqlalchemy import select

from src.data.storage import Forecast, Sounding, get_session, init_db

MODEL_NAME = "k_index_v1"
K_THRESHOLD = 22
STATION = "UUDD"


def main():
    logger.info("=" * 60)
    logger.info(f"Запись прогнозов {MODEL_NAME} (K >= {K_THRESHOLD})")
    logger.info("=" * 60)
    init_db()
    session = get_session()
    snd = pd.read_sql(
        select(Sounding.datetime, Sounding.K_index).where(
            Sounding.station == STATION,
            Sounding.K_index.isnot(None),
        ),
        session.bind,
    )
    logger.info(f"Загружено {len(snd)} звудирований")

    deleted = session.query(Forecast).filter(
        Forecast.station == STATION,
        Forecast.model_name == MODEL_NAME,
    ).delete()
    session.commit()
    if deleted:
        logger.info(f"Удалено старых: {deleted}")

    records = []
    for _, row in snd.iterrows():
        records.append(Forecast(
            station=STATION, datetime=row["datetime"],
            model_name=MODEL_NAME, lead_time_hours=12,
            predicts_groz=bool(row["K_index"] >= K_THRESHOLD),
            value=float(row["K_index"]),
        ))
    session.bulk_save_objects(records)
    session.commit()
    session.close()
    n_groz = sum(r.predicts_groz for r in records)
    logger.info(f"✅ Записано {len(records)} прогнозов, из них гроз: {n_groz}")


if __name__ == "__main__":
    main()
