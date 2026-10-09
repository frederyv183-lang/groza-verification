"""
Парсер ERA5 (pressure levels) → SQLite.
Запуск: python -m scripts.parse_era5
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr
from loguru import logger
from tqdm import tqdm

from app.config import settings
from src.data.storage import Sounding, get_session, init_db

ERA5_DIR = Path("data/raw/era5")
STATION = settings.STATION_ICAO
STATION_LAT = 55.75
STATION_LON = 37.5
LEVELS = [850, 700, 500]


def kelvin_to_celsius(t_k):
    return t_k - 273.15


def specific_humidity_to_dewpoint(q, p_hpa):
    if q is None or np.isnan(q) or q <= 0:
        return float("nan")
    e = q * p_hpa / (0.622 + 0.378 * q)
    if e <= 0:
        return float("nan")
    ln_e = np.log(e / 6.112)
    return 243.5 * ln_e / (17.67 - ln_e)


def k_index(t850, t700, t500, td850, td700):
    vals = [t850, t700, t500, td850, td700]
    if any(v is None or (isinstance(v, float) and np.isnan(v)) for v in vals):
        return float("nan")
    return (t850 - t500) + td850 - (t700 - td700)


def _safe(v):
    if v is None:
        return None
    try:
        if np.isnan(v):
            return None
    except (TypeError, ValueError):
        pass
    return float(v)


def find_station_point(ds):
    lat_name = "latitude" if "latitude" in ds.coords else "lat"
    lon_name = "longitude" if "longitude" in ds.coords else "lon"
    lats = ds[lat_name].values
    lons = ds[lon_name].values
    i_lat = int(np.argmin(np.abs(lats - STATION_LAT)))
    i_lon = int(np.argmin(np.abs(lons - STATION_LON)))
    logger.info(f"Ближайшая точка: lat={lats[i_lat]}, lon={lons[i_lon]}")
    return lat_name, lon_name, i_lat, i_lon


def extract_from_file(nc_path):
    logger.info(f"Читаю {nc_path.name}...")
    ds = xr.open_dataset(nc_path)
    try:
        lat_name, lon_name, i_lat, i_lon = find_station_point(ds)
        var_t = "t" if "t" in ds.data_vars else "temperature"
        var_q = "q" if "q" in ds.data_vars else "specific_humidity"
        var_z = "z" if "z" in ds.data_vars else "geopotential"
        time_name = "valid_time" if "valid_time" in ds.dims else "time"
        level_name = "pressure_level" if "pressure_level" in ds.dims else "level"

        lat_val = ds[lat_name].values[i_lat]
        lon_val = ds[lon_name].values[i_lon]

        rows = []
        times = ds[time_name].values
        for i_time, t in enumerate(tqdm(times, desc=nc_path.stem)):
            row = {"datetime": pd.to_datetime(t), "station": STATION}
            for lev in LEVELS:
                try:
                    sel = {level_name: lev, lat_name: lat_val, lon_name: lon_val}
                    t_val = float(ds[var_t].sel(sel, method="nearest").isel({time_name: i_time}).values)
                    q_val = float(ds[var_q].sel(sel, method="nearest").isel({time_name: i_time}).values)
                    z_val = float(ds[var_z].sel(sel, method="nearest").isel({time_name: i_time}).values)
                    row[f"T_{lev}"] = kelvin_to_celsius(t_val)
                    row[f"Td_{lev}"] = specific_humidity_to_dewpoint(q_val, float(lev))
                    row[f"Z_{lev}"] = z_val / 9.80665
                except Exception as e:
                    logger.warning(f"Уровень {lev}: {e}")
                    row[f"T_{lev}"] = np.nan
                    row[f"Td_{lev}"] = np.nan
                    row[f"Z_{lev}"] = np.nan
            row["K_index"] = k_index(
                row.get("T_850"), row.get("T_700"), row.get("T_500"),
                row.get("Td_850"), row.get("Td_700"),
            )
            row["LI"] = (row.get("T_500") or np.nan) - (row.get("T_850") or np.nan)
            rows.append(row)
        df = pd.DataFrame(rows)
        logger.info(f"  Извлечено {len(df)} сроков")
        return df
    finally:
        ds.close()


def save_to_db(df):
    session = get_session()
    try:
        deleted = session.query(Sounding).filter(Sounding.station == STATION).delete()
        session.commit()
        if deleted:
            logger.info(f"Удалено старых: {deleted}")
        records = []
        for _, row in tqdm(df.iterrows(), total=len(df), desc="Запись в SQLite"):
            records.append(Sounding(
                station=row["station"], datetime=row["datetime"], source="ERA5",
                T_850=_safe(row.get("T_850")), T_700=_safe(row.get("T_700")), T_500=_safe(row.get("T_500")),
                Td_850=_safe(row.get("Td_850")), Td_700=_safe(row.get("Td_700")), Td_500=_safe(row.get("Td_500")),
                Z_850=_safe(row.get("Z_850")), Z_700=_safe(row.get("Z_700")), Z_500=_safe(row.get("Z_500")),
                K_index=_safe(row.get("K_index")), LI=_safe(row.get("LI")),
            ))
        session.bulk_save_objects(records)
        session.commit()
        return len(records)
    finally:
        session.close()


def main():
    logger.info("=" * 60)
    logger.info("ПАРСЕР ERA5 → SQLite (soundings)")
    logger.info("=" * 60)
    init_db()
    files = sorted(ERA5_DIR.glob("era5_UUDD_*.nc"))
    if not files:
        logger.error(f"Не найдено .nc в {ERA5_DIR}")
        sys.exit(1)
    logger.info(f"Найдено {len(files)} файлов")
    all_dfs = [extract_from_file(f) for f in files]
    big = pd.concat(all_dfs, ignore_index=True)
    n = save_to_db(big)
    logger.info("=" * 60)
    logger.info(f"✅ Записано {n} звудирований")
    k = big["K_index"].dropna()
    if len(k) > 0:
        logger.info(f"K-индекс: min={k.min():.1f}, mean={k.mean():.1f}, max={k.max():.1f}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
