import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    APP_NAME: str = os.getenv("APP_NAME", 'Inversiones "El Profeta" - Gestión Comercial y Control de Capital')
    BUSINESS_NAME: str = os.getenv("BUSINESS_NAME", 'INVERSIONES "EL PROFETA"')
    BUSINESS_NIT: str = os.getenv("BUSINESS_NIT", "1020233725")
    BUSINESS_PHONE: str = os.getenv("BUSINESS_PHONE", "3024645363")
    BUSINESS_CITY: str = os.getenv("BUSINESS_CITY", "Colombia")

    APP_ENV: str = os.getenv("APP_ENV", "development")
    DEBUG: bool = os.getenv("DEBUG", "True").lower() in ("true", "1", "yes")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "clave-secreta-el-profeta-2026")
    ACCESS_PIN: str = os.getenv("ACCESS_PIN", "").strip()

    DEFAULT_COSTO_UNITARIO: float = float(os.getenv("DEFAULT_COSTO_UNITARIO", "2700"))
    DEFAULT_PRECIO_VENTA: float = float(os.getenv("DEFAULT_PRECIO_VENTA", "4000"))

    @property
    def database_url(self) -> str:
        raw_url = os.getenv("DATABASE_URL", "sqlite:///./isaias_papas.db").strip()
        # Compatibilidad automática con Render.com (postgres:// -> postgresql://)
        if raw_url.startswith("postgres://"):
            raw_url = raw_url.replace("postgres://", "postgresql://", 1)
        return raw_url


settings = Settings()


def format_cop(value: float | int | None) -> str:
    """Formatea un valor numérico en formato Pesos Colombianos ($ 4.000)."""
    if value is None:
        return "$ 0"
    try:
        num = round(float(value))
        sign = "-" if num < 0 else ""
        formatted = f"{abs(num):,}".replace(",", ".")
        return f"{sign}$ {formatted}"
    except (ValueError, TypeError):
        return "$ 0"
