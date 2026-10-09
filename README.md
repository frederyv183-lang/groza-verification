# Оценка успешности прогноза грозы — Домодедово

Проект для верификации прогнозов грозы для аэропорта Домодедово.

## Описание

Система собирает данные о фактических грозах (METAR/SPECI) и прогнозах
различных моделей (COSMO-Ru, метод Решетова, метод Фауста, индексы CAPE/K/LI),
рассчитывает метрики успешности (POD, FAR, CSI, HK) и визуализирует их.

## Структура

    groz_verification/
    ├── app/                  # Веб-приложение (FastAPI)
    │   ├── main.py
    │   ├── routes/
    │   ├── templates/
    │   └── static/
    ├── src/                  # Ядро логики
    │   ├── data/
    │   ├── metrics/
    │   └── models/
    ├── data/
    │   ├── raw/
    │   └── processed/
    ├── scripts/
    ├── tests/
    └── config/

## Быстрый старт

    python -m venv .venv
    .venv\Scripts\activate    # Windows
    pip install -r requirements.txt
    cp .env.example .env
    python -m app.main

Открыть: http://127.0.0.1:5000

## Метрики

- POD — Probability of Detection
- FAR — False Alarm Ratio
- CSI — Critical Success Index
- HK  — Критерий Пирса-Обухова
