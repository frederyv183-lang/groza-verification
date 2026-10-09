"""
Метрики верификации.
"""
import numpy as np
import pandas as pd
from loguru import logger


def confusion_matrix(y_true, y_pred) -> dict:
    y_true = np.asarray(y_true).astype(int)
    y_pred = np.asarray(y_pred).astype(int)
    return {
        "hits": int(np.sum((y_true == 1) & (y_pred == 1))),
        "misses": int(np.sum((y_true == 1) & (y_pred == 0))),
        "false_alarms": int(np.sum((y_true == 0) & (y_pred == 1))),
        "correct_negatives": int(np.sum((y_true == 0) & (y_pred == 0))),
    }


def pod(cm): 
    d = cm["hits"] + cm["misses"]
    return cm["hits"] / d if d > 0 else 0.0


def far(cm):
    d = cm["hits"] + cm["false_alarms"]
    return cm["false_alarms"] / d if d > 0 else 0.0


def csi(cm):
    d = cm["hits"] + cm["misses"] + cm["false_alarms"]
    return cm["hits"] / d if d > 0 else 0.0


def hk(cm):
    hits, misses = cm["hits"], cm["misses"]
    fa, cn = cm["false_alarms"], cm["correct_negatives"]
    p = hits / (hits + misses) if (hits + misses) > 0 else 0.0
    pofd = fa / (fa + cn) if (fa + cn) > 0 else 0.0
    return p - pofd


def all_metrics(y_true, y_pred) -> dict:
    cm = confusion_matrix(y_true, y_pred)
    return {**cm, "POD": pod(cm), "FAR": far(cm), "CSI": csi(cm), "HK": hk(cm)}


def metrics_by_lead_time(df: pd.DataFrame) -> pd.DataFrame:
    bins = [0, 2, 6, 12, 24, 999]
    labels = ["0-2h", "2-6h", "6-12h", "12-24h", ">24h"]
    df = df.copy()
    df["lead_bin"] = pd.cut(df["lead_time_hours"], bins=bins, labels=labels)
    results = []
    for label, group in df.groupby("lead_bin", observed=True):
        m = all_metrics(group["y_true"].values, group["y_pred"].values)
        m["lead_time"] = str(label)
        m["n"] = len(group)
        results.append(m)
    return pd.DataFrame(results)
