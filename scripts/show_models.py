"""
Просмотр сводной таблицы моделей.
Запуск: python -m scripts.show_models
"""
import numpy as np
import pandas as pd
from sqlalchemy import select
from src.data.storage import Fact, Forecast, get_session


def confusion(y_true, y_pred):
    y_true = np.asarray(y_true).astype(int)
    y_pred = np.asarray(y_pred).astype(int)
    h = int(np.sum((y_true == 1) & (y_pred == 1)))
    m = int(np.sum((y_true == 1) & (y_pred == 0)))
    f = int(np.sum((y_true == 0) & (y_pred == 1)))
    c = int(np.sum((y_true == 0) & (y_pred == 0)))
    return h, m, f, c


def calc_metrics(h, m, f, c):
    pod = h / (h + m) if (h + m) else 0
    far = f / (h + f) if (h + f) else 0
    csi = h / (h + m + f) if (h + m + f) else 0
    pofd = f / (f + c) if (f + c) else 0
    return pod, far, csi, pod - pofd


def main():
    session = get_session()
    try:
        models = session.execute(
            select(Forecast.model_name).distinct()
        ).scalars().all()
        if not models:
            print("Нет моделей в forecasts")
            return

        facts = pd.read_sql(
            select(Fact.datetime).where(
                Fact.station == "UUDD", Fact.has_groz == True),
            session.bind,
        )
        groz_days = set(pd.to_datetime(facts["datetime"]).dt.date.unique())

        rows = []
        for model in models:
            fc = pd.read_sql(
                select(Forecast.datetime, Forecast.predicts_groz).where(
                    Forecast.station == "UUDD",
                    Forecast.model_name == model,
                ),
                session.bind,
            )
            if fc.empty:
                continue
            fc["date"] = pd.to_datetime(fc["datetime"]).dt.date
            y_true = fc["date"].isin(groz_days).astype(int).values
            y_pred = fc["predicts_groz"].astype(int).values
            h, m, f, c = confusion(y_true, y_pred)
            pod, far, csi, hk = calc_metrics(h, m, f, c)
            rows.append({
                "Модель": model,
                "Прогнозов": len(fc),
                "С грозой": int(y_pred.sum()),
                "POD": round(pod, 3),
                "FAR": round(far, 3),
                "CSI": round(csi, 3),
                "HK": round(hk, 3),
            })

        df = pd.DataFrame(rows).sort_values("CSI", ascending=False)
        print("\n" + "=" * 90)
        print("  СВОДНАЯ ТАБЛИЦА МОДЕЛЕЙ ПРОГНОЗА ГРОЗ")
        print("=" * 90)
        print(df.to_string(index=False))
        print("=" * 90)
        print("\nPOD — доля обнаруженных гроз (чем больше, тем лучше)")
        print("FAR — доля ложных тревог (чем меньше, тем лучше)")
        print("CSI — критический индекс успешности (баланс, чем больше, тем лучше)")
        print("HK  — критерий Пирса-Обухова (учитывает всё, чем больше, тем лучше)\n")
    finally:
        session.close()


if __name__ == "__main__":
    main()
