"""
Парсер архива METAR (Iowa State ASOS) → SQLite.

Читает все CSV из data/raw/UUDD_*.csv,
выделяет грозы по колонкам `wxcodes` и `metar`,
записывает в таблицу `facts`.

Запуск:
    python -m scripts.parse_metar_archive
"""

import re
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
from loguru import logger
from sqlalchemy import select
from tqdm import tqdm

from app.config import settings
from src.data.storage import Fact, get_session, init_db

# ============================================================
#                    МАРКЕРЫ ГРОЗЫ
# ============================================================

# Регулярка: ищем TS как отдельное явление, но не как часть слова
# (например, "TS" в METAR, "TSRA", "TSGR", "VCTS", "TSSN", "+TSRA")
GROZ_PATTERN = re.compile(
    r"""
    (?<![A-Z])          # перед TS не должно быть букв
    (?:
        \+|-
    )?                   # опциональный знак интенсивности
    TS                   # собственно TS
    (?:
        RA|SN|GR|GS|PL|DZ|SH|   # осадки, связанные с грозой
        \b                       # или конец токена
    )
    """,
    re.VERBOSE,
)

# Простой поиск: если в строке есть подстрока, содержащая TS
# (более мягкий критерий — используется для колонки wxcodes)
SIMPLE_MARKERS = ["TS", "TSRA", "+TSRA", "-TSRA", "TSGR", "TSSN", "TSPL", "VCTS", "TSGS"]


def has_groz_in_metar(metar: str) -> bool:
    """Проверить, есть ли в тексте METAR признак грозы."""
    if not isinstance(metar, str):
        return False
    return bool(GROZ_PATTERN.search(metar))


def has_groz_in_wxcodes(wx: str) -> bool:
    """Проверить колонку wxcodes на наличие TS."""
    if not isinstance(wx, str):
        return False
    return any(marker in wx for marker in SIMPLE_MARKERS)


# ============================================================
#                    ОСНОВНАЯ ЛОГИКА
# ============================================================

def load_csvs() -> pd.DataFrame:
    """Загрузить и объединить все CSV из data/raw/."""
    raw_dir = Path(settings.DATA_RAW_DIR)
    files = sorted(raw_dir.glob("UUDD_*.csv"))

    if not files:
        logger.error(f"Не найдено ни одного CSV в {raw_dir}")
        sys.exit(1)

    logger.info(f"Найдено {len(files)} файлов:")
    for f in files:
        logger.info(f"  • {f.name} ({f.stat().st_size // 1024} КБ)")

    frames = []
    for f in tqdm(files, desc="Чтение CSV"):
        try:
            df = pd.read_csv(f, encoding="utf-8", on_bad_lines="skip", low_memory=False)
            logger.info(f"  {f.name}: {len(df)} строк, колонки: {list(df.columns)[:5]}...")
            frames.append(df)
        except Exception as e:
            logger.error(f"  Ошибка чтения {f.name}: {e}")

    if not frames:
        logger.error("Не удалось прочитать ни один файл")
        sys.exit(1)

    big = pd.concat(frames, ignore_index=True)
    logger.info(f"Объединено: {len(big)} строк")
    return big


def parse_datetime(s: str) -> datetime | None:
    """Распарсить колонку valid (формат 'YYYY-MM-DD HH:MM')."""
    try:
        return datetime.strptime(s.strip(), "%Y-%m-%d %H:%M")
    except (ValueError, AttributeError):
        return None


def process_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Обработать DataFrame:
    - распарсить datetime
    - найти грозы
    - оставить только нужные колонки
    """
    required = {"station", "valid", "metar"}
    missing = required - set(df.columns)
    if missing:
        logger.error(f"В CSV нет обязательных колонок: {missing}")
        sys.exit(1)

    # wxcodes может отсутствовать — создадим пустую
    if "wxcodes" not in df.columns:
        df["wxcodes"] = ""

    # Парсим datetime
    logger.info("Парсинг datetime...")
    df["datetime"] = df["valid"].apply(parse_datetime)
    df = df.dropna(subset=["datetime"])

    # Определяем грозы
    logger.info("Поиск гроз...")
    df["groz_metar"] = df["metar"].apply(has_groz_in_metar)
    df["groz_wx"] = df["wxcodes"].apply(has_groz_in_wxcodes)
    df["has_groz"] = df["groz_metar"] | df["groz_wx"]

    return df


def save_to_db(df: pd.DataFrame) -> dict:
    """Записать факты в SQLite."""
    session = get_session()

    # Удалим старые факты для UUDD (чтобы не дублировались)
    deleted = session.query(Fact).filter(Fact.station == settings.STATION_ICAO).delete()
    session.commit()
    if deleted:
        logger.info(f"Удалено старых записей: {deleted}")

    # Готовим объекты
    facts = []
    for _, row in tqdm(df.iterrows(), total=len(df), desc="Запись в SQLite"):
        facts.append(Fact(
            station=str(row["station"])[:4],
            datetime=row["datetime"],
            has_groz=bool(row["has_groz"]),
            raw_metar=str(row["metar"])[:500],  # ограничим длину
        ))

    # Bulk insert
    session.bulk_save_objects(facts)
    session.commit()

    stats = {
        "total": len(facts),
        "groz": int(df["has_groz"].sum()),
        "groz_metar": int(df["groz_metar"].sum()),
        "groz_wx": int(df["groz_wx"].sum()),
    }
    session.close()
    return stats


def print_stats(df: pd.DataFrame):
    """Вывести статистику по годам и месяцам."""
    groz_df = df[df["has_groz"]].copy()
    groz_df["year"] = groz_df["datetime"].dt.year
    groz_df["month"] = groz_df["datetime"].dt.month

    print("\n" + "=" * 60)
    print("  СТАТИСТИКА ПО АРХИВУ")
    print("=" * 60)
    print(f"  Всего METAR:        {len(df):>8}")
    print(f"  Грозовых сводок:    {len(groz_df):>8}")
    print(f"  Частота гроз:       {100 * len(groz_df) / len(df):>7.2f}%")
    print(f"  Уникальных дней с грозой: {groz_df['datetime'].dt.date.nunique():>8}")
    print("=" * 60)

    print("\n  Грозы по годам:")
    print("  " + "-" * 40)
    by_year = groz_df.groupby("year").agg(
        сводок=("has_groz", "size"),
        дней=("datetime", lambda x: x.dt.date.nunique()),
    )
    for year, row in by_year.iterrows():
        print(f"    {year}: {row['сводок']:>5} сводок, {row['дней']:>3} дней")

    print("\n  Грозы по месяцам (за все годы):")
    print("  " + "-" * 40)
    by_month = groz_df.groupby("month").agg(
        сводок=("has_groz", "size"),
        дней=("datetime", lambda x: x.dt.date.nunique()),
    )
    month_names = ["Янв", "Фев", "Мар", "Апр", "Май", "Июн",
                   "Июл", "Авг", "Сен", "Окт", "Ноя", "Дек"]
    for month, row in by_month.iterrows():
        print(f"    {month_names[month-1]}: {row['сводок']:>5} сводок, {row['дней']:>3} дней")
    print()


def main():
    logger.info("=" * 60)
    logger.info("ПАРСЕР METAR → SQLite")
    logger.info(f"Станция: {settings.STATION_NAME} ({settings.STATION_ICAO})")
    logger.info("=" * 60)

    # 1. Инициализация БД
    init_db()

    # 2. Загрузка CSV
    df = load_csvs()

    # 3. Обработка
    df = process_dataframe(df)

    # 4. Запись в БД
    stats = save_to_db(df)

    # 5. Статистика
    print_stats(df)

    logger.info("=" * 60)
    logger.info(f"✅ Готово! Записано {stats['total']} фактов, из них {stats['groz']} с грозой")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()