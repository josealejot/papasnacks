from pathlib import Path
from urllib.parse import quote
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from app.config import format_cop, settings

BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Registrar filtro global de moneda colombiana y configuración en Jinja2
templates.env.filters["cop"] = format_cop
templates.env.globals["settings"] = settings


def redirect_con_mensaje(url: str, mensaje: str, tipo: str = "exito") -> RedirectResponse:
    sep = "&" if "?" in url else "?"
    destino = f"{url}{sep}msg={quote(mensaje)}&tipo={quote(tipo)}"
    return RedirectResponse(url=destino, status_code=303)
