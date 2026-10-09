"""
Строгая модель: K >= 25.
Запуск: python -m scripts.replay_k_strict
"""
import pandas as pd
from loguru import logger
from sqlalchemy import select

from src.data.storage import Forecast, Sounding, get_session, init_db

MODEL = "k_strict_v1"
K_THRESHOLD = 25
STATION = "UUDD"


def main():
    logger.info(f"Запись прогнозов {MODEL} (K >= {K_THRESHOLD})")
    init_db()
    session = get_session()
    snd = pd.read_sql(
        select(Sounding.datetime, Sounding.K_index).where(
            Sounding.station == STATION,
            Sounding.K_index.isnot(None),
        ),
        session.bind,
    )
    session.query(Forecast).filter(
        Forecast.station == STATION, Forecast.model_name == MODEL,
    ).delete()
    session.commit()

    records = [
        Forecast(
            station=STATION, datetime=row["datetime"],
            model_name=MODEL, lead_time_hours=12,
            predicts_groz=bool(row["K_index"] >= K_THRESHOLD),
            value=float(row["K_index"]),
        )
        for _, row in snd.iterrows()
    ]
    session.bulk_save_objects(records)
    session.commit()
    n_groz = sum(r.predicts_groz for r in records)
    session.close()
    logger.info(f"✅ {MODEL}: {len(records)} прогнозов, гроз: {n_groz}")


if __name__ == "__main__":
    main()
