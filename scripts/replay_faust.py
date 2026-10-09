"""
Запись прогнозов метода Фауста (T_v > 0).
Запуск: python -m scripts.replay_faust
"""
import pandas as pd
from loguru import logger
from sqlalchemy import select

from src.data.storage import Forecast, Sounding, get_session, init_db

MODEL = "faust_v1"
TV_THRESHOLD = 0.0
STATION = "UUDD"


def main():
    logger.info(f"Запись прогнозов {MODEL} (T_v > {TV_THRESHOLD})")
    init_db()
    session = get_session()
    snd = pd.read_sql(
        select(Sounding.datetime, Sounding.T_850,
               Sounding.Td_850, Sounding.Td_700).where(
            Sounding.station == STATION,
            Sounding.T_850.isnot(None),
        ),
        session.bind,
    )
    snd["Td_mean"] = (snd["Td_850"] + snd["Td_700"]) / 2
    snd["T_v"] = 0.5 * (snd["T_850"] + snd["Td_mean"])

    session.query(Forecast).filter(
        Forecast.station == STATION, Forecast.model_name == MODEL,
    ).delete()
    session.commit()

    records = [
        Forecast(
            station=STATION, datetime=row["datetime"],
            model_name=MODEL, lead_time_hours=12,
            predicts_groz=bool(row["T_v"] > TV_THRESHOLD),
            value=float(row["T_v"]),
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
