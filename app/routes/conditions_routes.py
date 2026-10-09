"""Страница условий образования гроз."""
from pathlib import Path
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@router.get("/conditions", response_class=HTMLResponse, tags=["📚 Теория"])
async def conditions_page(request: Request):
    return templates.TemplateResponse("conditions.html", {"request": request})
