#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Парсинг скачанных .nc файлов → CSV.
Запускать ПОСЛЕ download_gfs_ncss.py.
"""

import os
import glob
import pandas as pd
import xarray as xr

BASE = r"C:\Users\Major\fog_project"
RAW_DIR = os.path.join(BASE, "data", "forecasts", "gfs_ncss", "raw")
CSV_DIR = os.path.join(BASE, "data", "forecasts", "gfs_ncss", "csv")

STATION_NAMES = {
    "domodedovo":   "Домодедово",
    "sheremetyevo": "Шереметьево",
    "lodeynoye":    "Лодейное_Поле",
    "pulkovo":      "Пулково",
}


def parse_station(station_slug):
    folder = os.path.join(RAW_DIR, station_slug)
    if not os.path.isdir(folder):
        print(f"  ⚠️ нет папки {folder}")
        return None

    files = sorted(glob.glob(os.path.join(folder, "*.nc")))
    print(f"  найдено {len(files)} файлов")

    rows = []
    errors = 0
    for fp in files:
        try:
            ds = xr.open_dataset(fp, engine="netcdf4")
            val = float(ds["Visibility_surface"].values[0])
            t = pd.to_datetime(ds["time"].values[0])
            ds.close()
            rows.append({"time": t, "visibility": val})
        except Exception as e:
            errors += 1
            print(f"    ⚠️ {os.path.basename(fp)}: {type(e).__name__}: {e}")
            if errors > 10:
                print("    слишком много ошибок, прерываю")
                break

    if not rows:
        return None

    df = pd.DataFrame(rows).sort_values("time").reset_index(drop=True)
    return df


def main():
    os.makedirs(CSV_DIR, exist_ok=True)

    for slug, name in STATION_NAMES.items():
        print(f"\n=== {name} ({slug}) ===")
        df = parse_station(slug)
        if df is None:
            print("  ⚠️ нет данных")
            continue
        out = os.path.join(CSV_DIR, f"{name}_2025.csv")
        df.to_csv(out, index=False)
        print(f"  ✅ {len(df)} строк → {out}")
        print(f"     диапазон: {df['time'].min()} .. {df['time'].max()}")
        print(f"     туманов (<1000 м): {(df['visibility'] < 1000).sum()}")


if __name__ == "__main__":
    main()