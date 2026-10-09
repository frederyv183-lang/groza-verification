"""
Расчёт метрик.
Запуск: python -m scripts.calculate_metrics
"""
from loguru import logger
from src.metrics.verification import all_metrics


def main():
    y_true = [1, 0, 1, 1, 0, 0, 1, 0]
    y_pred = [1, 0, 0, 1, 0, 1, 1, 0]
    metrics = all_metrics(y_true, y_pred)
    logger.info("Метрики верификации:")
    for k, v in metrics.items():
        if isinstance(v, float):
            logger.info(f"  {k}: {v:.4f}")
        else:
            logger.info(f"  {k}: {v}")


if __name__ == "__main__":
    main()
