"""
Комбинированная верификация: K-индекс + Фауст.
Запуск: python -m scripts.verify_combined
"""
import numpy as np
import pandas as pd
from loguru import logger
from sqlalchemy import select
from src.data.storage import Fact, Sounding, get_session

K_THRESHOLDS = [22, 23, 24, 25, 26, 27, 28]
TV_THRESHOLDS = [-5, -3, -2, -1, 0, 1, 2]


def load_data():
    session = get_session()
    snd = pd.read_sql(
        select(Sounding.datetime, Sounding.K_index, Sounding.T_850,
               Sounding.Td_850, Sounding.Td_700).where(
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
    snd["Td_mean"] = (snd["Td_850"] + snd["Td_700"]) / 2
    snd["T_v"] = 0.5 * (snd["T_850"] + snd["Td_mean"])
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
    logger.info("КОМБИНИРОВАННАЯ ВЕРИФИКАЦИЯ: K + Фауст")
    logger.info("=" * 70)
    df = load_data()
    y_true = df["is_groz_fact"].values
    print(f"\n{'K*':>4} {'Tv*':>5} {'H':>5} {'M':>5} {'F':>5} "
          f"{'POD':>7} {'FAR':>7} {'CSI':>7} {'HK':>7}")
    print("-" * 70)
    results = []
    for k_thr in K_THRESHOLDS:
        for tv_thr in TV_THRESHOLDS:
            y_pred = ((df["K_index"] >= k_thr) & (df["T_v"] > tv_thr)).astype(int)
            m = cm(y_true, y_pred)
            results.append({"k": k_thr, "tv": tv_thr, **m})
            print(f"{k_thr:>4} {tv_thr:>5} {m['H']:>5} {m['M']:>5} {m['F']:>5} "
                  f"{m['POD']:>7.3f} {m['FAR']:>7.3f} {m['CSI']:>7.3f} {m['HK']:>7.3f}")
    best = max(results, key=lambda r: r["CSI"])
    print(f"\nЛучший CSI: K>={best['k']} И T_v>{best['tv']} — CSI={best['CSI']:.3f}")


if __name__ == "__main__":
    main()
