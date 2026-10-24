from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.venta import Venta
from app.models.cliente import Cliente
from app.models.transaccion import Transaccion
from app.models.gasto import Gasto
from app.routes import templates, redirect_con_mensaje
from app.services.capital_service import registrar_abono, obtener_resumen_capital

router = APIRouter(prefix="/cartera", tags=["Cartera y Caja"])


@router.get("", response_class=HTMLResponse)
def vista_cartera(request: Request, q: str = "", db: Session = Depends(get_db)):
    facturas_pendientes = (
        db.query(Venta)
        .filter(Venta.estado.in_(["PENDIENTE", "PARCIAL"]), Venta.saldo_pendiente > 0)
        .order_by(Venta.fecha.asc())
        .all()
    )
    if q.strip():
        termino = q.strip().lower()
        facturas_pendientes = [
            v
            for v in facturas_pendientes
            if termino in v.numero_factura.lower()
            or (v.cliente and termino in v.cliente.nombre.lower())
        ]

    abonos_recientes = (
        db.query(Transaccion)
        .filter(Transaccion.tipo == "ABONO_CARTERA", Transaccion.anulada == False)
        .order_by(Transaccion.fecha.desc())
        .limit(15)
        .all()
    )
    gastos_recientes = db.query(Gasto).order_by(Gasto.fecha.desc()).limit(12).all()
    resumen = obtener_resumen_capital(db)

    clientes_con_deuda = [
        c for c in db.query(Cliente).filter(Cliente.activo == True).all() if c.deuda_total > 0
    ]
    clientes_con_deuda.sort(key=lambda c: c.deuda_total, reverse=True)

    return templates.TemplateResponse(
        request=request,
        name="cartera/index.html",
        context={
            "pagina_activa": "cartera",
            "facturas_pendientes": facturas_pendientes,
            "abonos_recientes": abonos_recientes,
            "gastos_recientes": gastos_recientes,
            "clientes_con_deuda": clientes_con_deuda,
            "resumen": resumen,
            "q": q,
        },
    )


@router.post("/abonar")
def procesar_abono(
    venta_id: int = Form(...),
    monto_efectivo: float = Form(0.0),
    monto_transferencia: float = Form(0.0),
    entidad_transferencia: str = Form("Transferencia / Nequi"),
    concepto: str = Form(""),
    origen: str = Form("/cartera"),
    db: Session = Depends(get_db),
):
    try:
        tx = registrar_abono(
            db=db,
            venta_id=venta_id,
            monto_efectivo=monto_efectivo,
            monto_transferencia=monto_transferencia,
            entidad_transferencia=entidad_transferencia,
            concepto=concepto,
        )
        return redirect_con_mensaje(
            origen,
            f"¡Abono registrado con éxito ({tx.codigo_recibo}) por $ {tx.monto_total:,.0f}!",
            "exito",
        )
    except ValueError as e:
        return redirect_con_mensaje(origen, str(e), "error")
