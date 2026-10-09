"""
Верификация K-индекса: перебор порогов.
Запуск: python -m scripts.verify_k_index
"""
import sys
import numpy as np
import pandas as pd
from loguru import logger
from sqlalchemy import select
from src.data.storage import Fact, Sounding, get_session

THRESHOLDS = [15, 17, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 32, 35, 40]


def load_data():
    session = get_session()
    snd = pd.read_sql(
        select(Sounding.datetime, Sounding.K_index).where(
            Sounding.station == "UUDD", Sounding.K_index.isnot(None)),
        session.bind,
    )
    snd["date"] = pd.to_datetime(snd["datetime"]).dt.date
    facts = pd.read_sql(
        select(Fact.datetime).where(Fact.station == "UUDD", Fact.has_groz == True),
        session.bind,
    )
    groz_days = set(pd.to_datetime(facts["datetime"]).dt.date.unique())
    snd["is_groz_fact"] = snd["date"].isin(groz_days).astype(int)
    session.close()
    return snd


def cm(y_true, y_pred):
    y_true = np.asarray(y_true).astype(int)
    y_pred = np.asarray(y_pred).astype(int)
    h = int(np.sum((y_true == 1) & (y_pred == 1)))
    m = int(np.sum((y_true == 1) & (y_pred == 0)))
    f = int(np.sum((y_true == 0) & (y_pred == 1)))
    c = int(np.sum((y_true == 0) & (y_pred == 0)))
    pod = h / (h + m) if (h + m) else 0
    far = f / (h + f) if (h + f) else 0
    csi = h / (h + m + f) if (h + m + f) else 0
    pofd = f / (f + c) if (f + c) else 0
    return {"H": h, "M": m, "F": f, "C": c,
            "POD": pod, "FAR": far, "CSI": csi, "HK": pod - pofd}


def main():
    logger.info("=" * 70)
    logger.info("ВЕРИФИКАЦИЯ K-ИНДЕКСА")
    logger.info("=" * 70)
    df = load_data()
    y_true = df["is_groz_fact"].values
    print(f"\n{'Порог':>6} {'H':>5} {'M':>5} {'F':>5} {'POD':>7} {'FAR':>7} {'CSI':>7} {'HK':>7}")
    print("-" * 70)
    results = []
    for thr in THRESHOLDS:
        y_pred = (df["K_index"].values >= thr).astype(int)
        m = cm(y_true, y_pred)
        results.append({"threshold": thr, **m})
        print(f"{thr:>6} {m['H']:>5} {m['M']:>5} {m['F']:>5} "
              f"{m['POD']:>7.3f} {m['FAR']:>7.3f} {m['CSI']:>7.3f} {m['HK']:>7.3f}")
    best = max(results, key=lambda r: r["CSI"])
    print(f"\nЛучший CSI: K >= {best['threshold']} — CSI={best['CSI']:.3f}")


if __name__ == "__main__":
    main()
