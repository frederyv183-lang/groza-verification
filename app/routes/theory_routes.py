"""Страницы теории и метрик."""
from pathlib import Path
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@router.get("/theory", response_class=HTMLResponse, tags=["📚 Теория"])
async def theory_page(request: Request):
    return templates.TemplateResponse("theory.html", {"request": request})


@router.get("/metrics-view", response_class=HTMLResponse, tags=["📚 Теория"])
async def metrics_view(request: Request):
    return templates.TemplateResponse("metrics.html", {"request": request})


@router.get("/analytics", response_class=HTMLResponse, tags=["📉 Аналитика"])
async def analytics_page(request: Request):
    return templates.TemplateResponse("analytics.html", {"request": request})
