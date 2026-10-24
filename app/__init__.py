from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse

from app.config import settings
from app.database import Base, engine, SessionLocal
from app.models import Cliente, Producto, MovimientoInventario
from app.routes import templates
from app.routes.dashboard import router as dashboard_router
from app.routes.clientes import router as clientes_router
from app.routes.inventario import router as inventario_router
from app.routes.ventas import router as ventas_router
from app.routes.cartera import router as cartera_router
from app.routes.reportes import router as reportes_router


def inicializar_datos_semilla():
    """Crea las tablas y carga el catálogo base de snacks ($2.700 costo / $4.000 venta) si la BD está vacía."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(Cliente).count() == 0:
            clientes_base = [
                Cliente(
                    nombre="Cliente Mostrador (Venta Directa)",
                    documento="222222222",
                    telefono="",
                    direccion="Punto de Venta",
                    tipo_cliente="Detal",
                    cupo_credito=100000.0,
                    notas="Cliente predeterminado para ventas rápidas al contado.",
                ),
                Cliente(
                    nombre="Tienda y Cafetería La Esquina",
                    documento="900123456-1",
                    telefono="310 555 1234",
                    direccion="Calle Principal # 10-25",
                    tipo_cliente="Tienda / Punto",
                    cupo_credito=500000.0,
                    notas="Pedido frecuente semanal de snacks.",
                ),
                Cliente(
                    nombre="Miscelánea y Refrescos Don Pedro",
                    documento="79456123",
                    telefono="315 888 9900",
                    direccion="Barrio Centro Local 4",
                    tipo_cliente="Mayorista",
                    cupo_credito=800000.0,
                    notas="Paga mixto entre efectivo y Nequi.",
                ),
            ]
            db.add_all(clientes_base)
            db.commit()

        if db.query(Producto).count() == 0:
            costo_base = settings.DEFAULT_COSTO_UNITARIO  # 2700
            precio_base = settings.DEFAULT_PRECIO_VENTA   # 4000
            snacks_base = [
                Producto(
                    codigo="SNK-001",
                    nombre="Papas Snack Tradicional",
                    sabor="Natural / Sal",
                    presentacion="Paquete Individual",
                    costo_compra=costo_base,
                    precio_venta=precio_base,
                    stock_actual=100,
                    stock_minimo=20,
                ),
                Producto(
                    codigo="SNK-002",
                    nombre="Papas Snack Limón",
                    sabor="Limón Intenso",
                    presentacion="Paquete Individual",
                    costo_compra=costo_base,
                    precio_venta=precio_base,
                    stock_actual=60,
                    stock_minimo=15,
                ),
                Producto(
                    codigo="SNK-003",
                    nombre="Papas Snack Pollo",
                    sabor="Pollo Asado",
                    presentacion="Paquete Individual",
                    costo_compra=costo_base,
                    precio_venta=precio_base,
                    stock_actual=50,
                    stock_minimo=15,
                ),
                Producto(
                    codigo="SNK-004",
                    nombre="Papas Snack Picante",
                    sabor="Picante Fuego",
                    presentacion="Paquete Individual",
                    costo_compra=costo_base,
                    precio_venta=precio_base,
                    stock_actual=40,
                    stock_minimo=15,
                ),
            ]
            db.add_all(snacks_base)
            db.flush()

            for p in snacks_base:
                mov = MovimientoInventario(
                    producto_id=p.id,
                    tipo="AJUSTE_POSITIVO",
                    cantidad=p.stock_actual,
                    stock_resultante=p.stock_actual,
                    costo_unitario=p.costo_compra,
                    costo_total=round(p.stock_actual * p.costo_compra, 2),
                    proveedor="Inventario Inicial",
                    metodo_pago="N/A",
                    observacion="Stock inicial de apertura del sistema",
                )
                db.add(mov)
            db.commit()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    inicializar_datos_semilla()
    yield


def create_app() -> FastAPI:
    application = FastAPI(
        title=settings.APP_NAME,
        version="2.0.0",
        lifespan=lifespan,
    )

    static_dir = Path(__file__).resolve().parent / "static"
    application.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    # Middleware opcional de PIN de seguridad (si ACCESS_PIN está configurado en .env / Render)
    @application.middleware("http")
    async def pin_security_middleware(request: Request, call_next):
        pin_requerido = settings.ACCESS_PIN
        if pin_requerido:
            ruta = request.url.path
            if not (ruta.startswith("/static") or ruta.startswith("/pin-login") or ruta == "/health"):
                cookie_pin = request.cookies.get("isaias_auth_pin", "")
                if cookie_pin != pin_requerido:
                    return RedirectResponse(url="/pin-login", status_code=303)
        return await call_next(request)

    @application.get("/pin-login", response_class=HTMLResponse)
    def vista_pin_login(request: Request, error: str = ""):
        return templates.TemplateResponse(
            request=request,
            name="components/pin_login.html",
            context={"error": error},
        )

    @application.post("/pin-login")
    def validar_pin(pin: str = Form(...)):
        if pin.strip() == settings.ACCESS_PIN:
            response = RedirectResponse(url="/", status_code=303)
            response.set_cookie(key="isaias_auth_pin", value=settings.ACCESS_PIN, httponly=True, max_age=86400 * 30)
            return response
        return RedirectResponse(url="/pin-login?error=PIN+incorrecto", status_code=303)

    @application.get("/health")
    def healthcheck():
        return {"status": "ok", "business": settings.BUSINESS_NAME}

    application.include_router(dashboard_router)
    application.include_router(ventas_router)
    application.include_router(cartera_router)
    application.include_router(inventario_router)
    application.include_router(clientes_router)
    application.include_router(reportes_router)

    return application


app = create_app()
