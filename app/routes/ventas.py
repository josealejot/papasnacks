from typing import List
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.cliente import Cliente
from app.models.producto import Producto
from app.models.venta import Venta
from app.routes import templates, redirect_con_mensaje
from app.services.capital_service import registrar_venta, anular_venta

router = APIRouter(prefix="/ventas", tags=["Ventas"])


@router.get("", response_class=HTMLResponse)
def vista_ventas(
    request: Request,
    estado: str = "TODAS",
    q: str = "",
    db: Session = Depends(get_db),
):
    clientes = db.query(Cliente).filter(Cliente.activo == True).order_by(Cliente.nombre.asc()).all()
    productos = db.query(Producto).filter(Producto.activo == True).order_by(Producto.id.asc()).all()

    query = db.query(Venta)
    if estado in ("PAGADO", "PARCIAL", "PENDIENTE", "ANULADA"):
        query = query.filter(Venta.estado == estado)
    else:
        query = query.filter(Venta.estado != "ANULADA")

    ventas = query.order_by(Venta.fecha.desc()).all()
    if q.strip():
        termino = q.strip().lower()
        ventas = [
            v
            for v in ventas
            if termino in v.numero_factura.lower()
            or (v.cliente and termino in v.cliente.nombre.lower())
        ]

    return templates.TemplateResponse(
        request=request,
        name="ventas/index.html",
        context={
            "pagina_activa": "ventas",
            "clientes": clientes,
            "productos": productos,
            "ventas": ventas,
            "estado_filtro": estado,
            "q": q,
        },
    )


@router.post("/crear")
async def procesar_nueva_venta(
    request: Request,
    db: Session = Depends(get_db),
):
    form = await request.form()
    cliente_id = int(form.get("cliente_id", 0))
    descuento = float(form.get("descuento") or 0.0)
    pagado_efectivo = float(form.get("pagado_efectivo") or 0.0)
    pagado_transferencia = float(form.get("pagado_transferencia") or 0.0)
    referencia_transferencia = str(form.get("referencia_transferencia") or "")
    notas = str(form.get("notas") or "")

    producto_ids = form.getlist("producto_id")
    cantidades = form.getlist("cantidad")
    precios = form.getlist("precio_unitario")

    items = []
    for idx, p_id in enumerate(producto_ids):
        if not p_id:
            continue
        cant = int(cantidades[idx]) if idx < len(cantidades) and cantidades[idx] else 0
        precio = float(precios[idx]) if idx < len(precios) and precios[idx] else None
        if cant > 0:
            items.append(
                {
                    "producto_id": int(p_id),
                    "cantidad": cant,
                    "precio_unitario": precio,
                }
            )

    try:
        venta = registrar_venta(
            db=db,
            cliente_id=cliente_id,
            items=items,
            pagado_efectivo=pagado_efectivo,
            pagado_transferencia=pagado_transferencia,
            descuento=descuento,
            referencia_transferencia=referencia_transferencia,
            notas=notas,
        )
        return redirect_con_mensaje(
            "/ventas",
            f"¡Venta {venta.numero_factura} registrada! Total: $ {venta.total_venta:,.0f} ({venta.estado}).",
            "exito",
        )
    except ValueError as e:
        return redirect_con_mensaje("/ventas", str(e), "error")


@router.get("/{venta_id}", response_class=HTMLResponse)
def detalle_venta(venta_id: int, request: Request, db: Session = Depends(get_db)):
    venta = db.query(Venta).filter(Venta.id == venta_id).first()
    if not venta:
        return redirect_con_mensaje("/ventas", "La factura solicitada no existe.", "error")

    return templates.TemplateResponse(
        request=request,
        name="ventas/detalle.html",
        context={
            "pagina_activa": "ventas",
            "venta": venta,
        },
    )


@router.post("/{venta_id}/anular")
def anular_factura_endpoint(venta_id: int, db: Session = Depends(get_db)):
    try:
        venta = anular_venta(db, venta_id)
        return redirect_con_mensaje(
            "/ventas",
            f"Factura {venta.numero_factura} anulada y unidades devueltas al inventario.",
            "alerta",
        )
    except ValueError as e:
        return redirect_con_mensaje("/ventas", str(e), "error")
