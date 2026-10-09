"""
Точка входа FastAPI-приложения.
"""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from loguru import logger

from app.config import settings
from app.routes import (
    data_routes, metrics_routes, forecast_routes,
    theory_routes, analytics_routes, conditions_routes,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Запуск {settings.APP_NAME}")
    logger.info(f"Станция: {settings.STATION_NAME} ({settings.STATION_ICAO})")
    yield
    logger.info("Остановка приложения")


app = FastAPI(
    title="Грозпроверка",
    description="Оценка успешности прогноза грозы для аэропорта Домодедово",
    version="0.4.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url=None,
    swagger_ui_parameters={
        "syntaxHighlight.theme": "monokai",
        "tryItOutEnabled": True,
        "docExpansion": "list",
        "filter": True,
    },
)

BASE_DIR = Path(__file__).parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR.mkdir(exist_ok=True)
TEMPLATES_DIR.mkdir(exist_ok=True)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

app.include_router(data_routes.router, prefix="/api/data", tags=["📊 Данные"])
app.include_router(metrics_routes.router, prefix="/api/metrics", tags=["📈 Метрики"])
app.include_router(analytics_routes.router, prefix="/api/analytics", tags=["📉 Аналитика"])
app.include_router(forecast_routes.router, prefix="/api/forecast", tags=["🔮 Прогнозы"])
app.include_router(theory_routes.router, tags=["📚 Теория"])
app.include_router(conditions_routes.router, tags=["🌩️ Условия"])


@app.get("/", response_class=HTMLResponse, tags=["🏠 Интерфейс"])
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "title": "Грозпроверка"})


@app.get("/health", tags=["🏠 Интерфейс"])
async def health():
    return {"status": "ok", "app": "Грозпроверка"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.DEBUG,
    )
