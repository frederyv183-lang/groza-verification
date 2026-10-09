"""
Метод прогноза гроз Г. Д. Решетова.
"""
from dataclasses import dataclass


@dataclass
class ReshetovInput:
    H_vg: float
    T_vg: float
    dH: float


def predict_groz(data: ReshetovInput) -> bool:
    if data.H_vg >= 6.0 and data.T_vg <= -23.0 and data.dH >= 3.0:
        return True
    return False
