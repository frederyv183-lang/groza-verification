"""
Классические индексы неустойчивости.
"""
from dataclasses import dataclass


@dataclass
class SoundingData:
    T_850: float
    T_700: float
    T_500: float
    Td_850: float
    Td_700: float
    Td_500: float


def k_index(data: SoundingData) -> float:
    return (data.T_850 - data.T_500) + data.Td_850 - (data.T_700 - data.Td_700)


def li_index(data: SoundingData) -> float:
    return data.T_500 - (data.T_850 - 6.5)


def has_groz_by_k(data: SoundingData) -> bool:
    return k_index(data) > 35
