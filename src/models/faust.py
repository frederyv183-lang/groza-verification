"""
Метод прогноза гроз Фауста.
"""
from dataclasses import dataclass


@dataclass
class FaustInput:
    T_v: float
    T_500: float


def predict_groz(data: FaustInput) -> bool:
    return data.T_v > 0
