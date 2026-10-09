"""
Расчёт индексов неустойчивости для существующих soundings.
Формулы из Богаткина (2010) и ВКР Иванова (2018).

Запуск:
    python -m scripts.calculate_indices
"""

import numpy as np
from loguru import logger
from sqlalchemy import select

from src.data.storage import Sounding, get_session, init_db


def _d(t, td):
    """Дефицит точки росы: D = T − Td. None если нет данных."""
    if t is None or td is None:
        return None
    return t - td


def ki_index(t850, t500, td850, d700):
    """
    Ki = (T850 − T500) + Td850 − D700  (Богаткин 2010, формула 2.5)
    Порог: <20 нет, 20–25 изолир., 25–30 отдельные, >30 повсеместно.
    """
    if any(v is None for v in [t850, t500, td850, d700]):
        return None
    return (t850 - t500) + td850 - d700


def vt_index(t850, t500):
    """VT = T850 − T500. Порог: >28 — неустойчиво."""
    if t850 is None or t500 is None:
        return None
    return t850 - t500


def ct_index(td850, t500):
    """CT = Td850 − T500. Порог: >18 — умеренно, >22 — сильные грозы."""
    if td850 is None or t500 is None:
        return None
    return td850 - t500


def tt_index(vt, ct):
    """TT = VT + CT. Порог: <44 нет, 44–45 отдельные, >55 смерчи."""
    if vt is None or ct is None:
        return None
    return vt + ct


def fateev_a(t850, t500, d850, d700, d500):
    """
    Фатеев (упрощённо, без 600 гПа):
    A = (T850 − T500) − (D850 + D700 + D500)
    Порог: A >= 0 → гроза.
    """
    if any(v is None for v in [t850, t500, d850, d700, d500]):
        return None
    return (t850 - t500) - (d850 + d700 + d500)


def lebedev_sd(d850, d700, d500):
    """ΣD Лебедевой = D850 + D700 + D500. Порог: >25 → гроз нет."""
    if any(v is None for v in [d850, d700, d500]):
        return None
    return d850 + d700 + d500


def bailey_no_groz(d850, d700, d500, t850, t500, z500):
    """
    Метод Бейли: TRUE если ЛЮБОЙ из 5 признаков отсутствия грозы выполнен.
    1) D850 >= 13 или D700 >= 13
    2) D700 + D500 >= 28 (упрощённо, вместо D600)
    3) (пропущено: адвекция сухого воздуха — нет данных)
    4) Вертикальный градиент 850–500 <= 0.5 °C/100 м
    5) Уровень T=-12°C ниже 3600 м (упрощённо: если T500 > -12 → нет)
    """
    if d850 is None or d700 is None:
        return None

    # Признак 1
    if d850 >= 13 or d700 >= 13:
        return True

    # Признак 2
    if d500 is not None and (d700 + d500) >= 28:
        return True

    # Признак 4
    if all(v is not None for v in [t850, t500, z500]):
        dz = z500 - 1500  # от 850 до 500 гПа в гп.м
        if dz > 0:
            gamma = (t850 - t500) / (dz / 100)  # °C/100 м
            if gamma <= 0.5:
                return True

    # Признак 5 (упрощённо)
    if t500 is not None and t500 > -12:
        return True

    return False


def main():
    logger.info("=" * 60)
    logger.info("РАСЧЁТ ИНДЕКСОВ НЕУСТОЙЧИВОСТИ")
    logger.info("=" * 60)

    init_db()
    session = get_session()

    rows = session.execute(select(Sounding)).scalars().all()
    logger.info(f"Загружено {len(rows)} звудирований")

    n_updated = 0
    for s in rows:
        d850 = _d(s.T_850, s.Td_850)
        d700 = _d(s.T_700, s.Td_700)
        d500 = _d(s.T_500, s.Td_500)

        s.Ki = ki_index(s.T_850, s.T_500, s.Td_850, d700)
        s.VT = vt_index(s.T_850, s.T_500)
        s.CT = ct_index(s.Td_850, s.T_500)
        s.TT = tt_index(s.VT, s.CT)
        s.Fateev_A = fateev_a(s.T_850, s.T_500, d850, d700, d500)
        s.Lebedeva_SD = lebedev_sd(d850, d700, d500)
        s.Bailey_no_groz = bailey_no_groz(
            d850, d700, d500, s.T_850, s.T_500, s.Z_500
        )
        n_updated += 1

    session.commit()
    session.close()

    logger.info(f"✅ Обновлено {n_updated} записей")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
