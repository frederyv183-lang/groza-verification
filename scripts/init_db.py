"""
Инициализация БД.
Запуск: python -m scripts.init_db
"""
from loguru import logger
from src.data.storage import init_db


def main():
    logger.info("Инициализация БД...")
    init_db()
    logger.info("Готово.")


if __name__ == "__main__":
    main()
