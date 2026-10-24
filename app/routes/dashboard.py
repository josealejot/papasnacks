from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.venta import Venta
from app.models.transaccion import Transaccion
from app.models.cliente import Cliente
from app.models.producto import Producto
from app.routes import templates, redirect_con_mensaje
from app.services.capital_service import (
    obtener_resumen_capital,
    registrar_movimiento_capital,
    registrar_gasto_operativo,
)

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
def vista_dashboard(request: Request, db: Session = Depends(get_db)):
    resumen = obtener_resumen_capital(db)
    ultimas_ventas = (
        db.query(Venta)
        .filter(Venta.estado != "ANULADA")
        .order_by(Venta.fecha.desc())
        .limit(8)
        .all()
    )
    ultimas_transacciones = (
        db.query(Transaccion)
        .filter(Transaccion.anulada == False)
        .order_by(Transaccion.fecha.desc())
        .limit(8)
        .all()
    )
    facturas_por_cobrar = (
        db.query(Venta)
        .filter(Venta.estado.in_(["PENDIENTE", "PARCIAL"]), Venta.saldo_pendiente > 0)
        .order_by(Venta.saldo_pendiente.desc())
        .limit(6)
        .all()
    )
    clientes = db.query(Cliente).filter(Cliente.activo == True).order_by(Cliente.nombre.asc()).all()
    productos = db.query(Producto).filter(Producto.activo == True).order_by(Producto.nombre.asc()).all()

    return templates.TemplateResponse(
        request=request,
        name="dashboard/index.html",
        context={
            "pagina_activa": "dashboard",
            "resumen": resumen,
            "ultimas_ventas": ultimas_ventas,
            "ultimas_transacciones": ultimas_transacciones,
            "facturas_por_cobrar": facturas_por_cobrar,
            "clientes": clientes,
            "productos": productos,
        },
    )


@router.post("/capital/movimiento")
def crear_movimiento_capital(
    tipo: str = Form(...),
    monto_efectivo: float = Form(0.0),
    monto_transferencia: float = Form(0.0),
    concepto: str = Form(""),
    entidad_transferencia: str = Form("Transferencia Electrónica"),
    db: Session = Depends(get_db),
):
    try:
        registrar_movimiento_capital(
            db=db,
            tipo=tipo,
            monto_efectivo=monto_efectivo,
            monto_transferencia=monto_transferencia,
            concepto=concepto,
            entidad_transferencia=entidad_transferencia,
        )
        return redirect_con_mensaje("/", "Movimiento de capital registrado correctamente.", "exito")
    except ValueError as e:
        return redirect_con_mensaje("/", str(e), "error")


@router.post("/capital/gasto")
def crear_gasto_rapido(
    categoria: str = Form("FLETE_TRANSPORTE"),
    descripcion: str = Form(...),
    monto_total: float = Form(...),
    pagado_efectivo: float = Form(0.0),
    pagado_transferencia: float = Form(0.0),
    proveedor: str = Form(""),
    origen: str = Form("/"),
    db: Session = Depends(get_db),
):
    try:
        registrar_gasto_operativo(
            db=db,
            categoria=categoria,
            descripcion=descripcion,
            monto_total=monto_total,
            pagado_efectivo=pagado_efectivo,
            pagado_transferencia=pagado_transferencia,
            proveedor=proveedor,
        )
        return redirect_con_mensaje(origen, "Gasto operativo registrado y descontado de caja/bancos.", "exito")
    except ValueError as e:
        return redirect_con_mensaje(origen, str(e), "error")
