"""Человекочитаемые названия моделей и утилиты."""
MODEL_LABELS = {
    "k_index_v1": "K-индекс (K ≥ 22)",
    "k_strict_v1": "K-индекс строгий (K ≥ 25)",
    "faust_v1": "Метод Фауста (T_v > 0)",
    "k_and_faust": "K + Фауст (K ≥ 22 и T_v > 0)",
    "reshetov_v1": "Метод Решетова",
}

MODEL_SHORT = {
    "k_index_v1": "K ≥ 22",
    "k_strict_v1": "K ≥ 25",
    "faust_v1": "T_v > 0",
    "k_and_faust": "K + Фауст",
}


def label(model_id: str) -> str:
    return MODEL_LABELS.get(model_id, model_id)


def short(model_id: str) -> str:
    return MODEL_SHORT.get(model_id, model_id)
