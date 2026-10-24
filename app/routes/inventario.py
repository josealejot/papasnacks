from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.producto import Producto, MovimientoInventario
from app.routes import templates, redirect_con_mensaje
from app.services.capital_service import registrar_entrada_inventario

router = APIRouter(prefix="/inventario", tags=["Inventario"])


@router.get("", response_class=HTMLResponse)
def vista_inventario(request: Request, db: Session = Depends(get_db)):
    productos = db.query(Producto).filter(Producto.activo == True).order_by(Producto.id.asc()).all()
    movimientos = (
        db.query(MovimientoInventario)
        .order_by(MovimientoInventario.fecha.desc())
        .limit(25)
        .all()
    )

    total_unidades = sum(max(p.stock_actual, 0) for p in productos)
    capital_costo = round(sum(p.valor_inventario_costo for p in productos), 2)
    capital_venta = round(sum(p.valor_inventario_venta for p in productos), 2)
    ganancia_potencial = round(sum(p.utilidad_potencial_stock for p in productos), 2)

    return templates.TemplateResponse(
        request=request,
        name="inventario/index.html",
        context={
            "pagina_activa": "inventario",
            "productos": productos,
            "movimientos": movimientos,
            "total_unidades": total_unidades,
            "capital_costo": capital_costo,
            "capital_venta": capital_venta,
            "ganancia_potencial": ganancia_potencial,
        },
    )


@router.post("/crear")
def crear_producto(
    codigo: str = Form(""),
    nombre: str = Form(...),
    sabor: str = Form("Tradicional"),
    presentacion: str = Form("Paquete Unidad"),
    costo_compra: float = Form(2700.0),
    precio_venta: float = Form(4000.0),
    stock_actual: int = Form(0),
    stock_minimo: int = Form(20),
    db: Session = Depends(get_db),
):
    nombre_limpio = nombre.strip()
    if not codigo.strip():
        total_prods = db.query(Producto).count() + 1
        codigo_final = f"SNK-{total_prods:03d}"
    else:
        codigo_final = codigo.strip().upper()

    existente = db.query(Producto).filter(Producto.codigo == codigo_final).first()
    if existente:
        return redirect_con_mensaje("/inventario", f"El código '{codigo_final}' ya está en uso.", "error")

    nuevo = Producto(
        codigo=codigo_final,
        nombre=nombre_limpio,
        sabor=sabor.strip() or "Tradicional",
        presentacion=presentacion.strip() or "Paquete Unidad",
        costo_compra=max(float(costo_compra), 0.0),
        precio_venta=max(float(precio_venta), 1.0),
        stock_actual=max(int(stock_actual), 0),
        stock_minimo=max(int(stock_minimo), 0),
        activo=True,
    )
    db.add(nuevo)
    db.flush()

    if nuevo.stock_actual > 0:
        mov = MovimientoInventario(
            producto_id=nuevo.id,
            tipo="AJUSTE_POSITIVO",
            cantidad=nuevo.stock_actual,
            stock_resultante=nuevo.stock_actual,
            costo_unitario=nuevo.costo_compra,
            costo_total=round(nuevo.stock_actual * nuevo.costo_compra, 2),
            proveedor="Inventario Inicial",
            metodo_pago="N/A",
            observacion="Carga de stock inicial al crear producto",
        )
        db.add(mov)

    db.commit()
    return redirect_con_mensaje("/inventario", f"Snack '{nuevo.nombre}' agregado al catálogo.", "exito")


@router.post("/{producto_id}/editar")
def editar_producto(
    producto_id: int,
    nombre: str = Form(...),
    sabor: str = Form("Tradicional"),
    presentacion: str = Form("Paquete Unidad"),
    costo_compra: float = Form(2700.0),
    precio_venta: float = Form(4000.0),
    stock_minimo: int = Form(20),
    db: Session = Depends(get_db),
):
    prod = db.query(Producto).filter(Producto.id == producto_id).first()
    if not prod:
        return redirect_con_mensaje("/inventario", "Producto no encontrado.", "error")

    prod.nombre = nombre.strip()
    prod.sabor = sabor.strip()
    prod.presentacion = presentacion.strip()
    prod.costo_compra = max(float(costo_compra), 0.0)
    prod.precio_venta = max(float(precio_venta), 1.0)
    prod.stock_minimo = max(int(stock_minimo), 0)
    db.commit()
    return redirect_con_mensaje("/inventario", f"Producto '{prod.nombre}' actualizado correctamente.", "exito")


@router.post("/entrada")
def entrada_lote_proveedor(
    producto_id: int = Form(...),
    cantidad: int = Form(...),
    costo_unitario: float = Form(2700.0),
    pagado_efectivo: float = Form(0.0),
    pagado_transferencia: float = Form(0.0),
    proveedor: str = Form("Proveedor de Snacks"),
    observacion: str = Form(""),
    afectar_caja: str = Form("si"),
    db: Session = Depends(get_db),
):
    try:
        mov = registrar_entrada_inventario(
            db=db,
            producto_id=producto_id,
            cantidad=cantidad,
            costo_unitario=costo_unitario,
            pagado_efectivo=pagado_efectivo,
            pagado_transferencia=pagado_transferencia,
            proveedor=proveedor,
            observacion=observacion,
            afectar_caja=(afectar_caja == "si"),
        )
        return redirect_con_mensaje(
            "/inventario",
            f"¡Entrada exitosa! +{mov.cantidad} unidades agregadas al stock.",
            "exito",
        )
    except ValueError as e:
        return redirect_con_mensaje("/inventario", str(e), "error")
