"""HTML page rendering routes."""

import os
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter(tags=["pages"])

# Configure templates
templates_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
templates = Jinja2Templates(directory=templates_path)


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Render the main viewer page."""
    return templates.TemplateResponse("viewer.html", {"request": request})


@router.get("/recordings.html", response_class=HTMLResponse)
async def recordings_page(request: Request):
    """Render the recordings page."""
    return templates.TemplateResponse("recordings.html", {"request": request})
