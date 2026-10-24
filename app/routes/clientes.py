from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.cliente import Cliente
from app.models.venta import Venta
from app.routes import templates, redirect_con_mensaje

router = APIRouter(prefix="/clientes", tags=["Clientes"])


@router.get("", response_class=HTMLResponse)
def listar_clientes(
    request: Request,
    q: str = "",
    filtro: str = "todos",
    db: Session = Depends(get_db),
):
    query = db.query(Cliente).filter(Cliente.activo == True)
    if q.strip():
        busqueda = f"%{q.strip()}%"
        query = query.filter(
            (Cliente.nombre.ilike(busqueda))
            | (Cliente.telefono.ilike(busqueda))
            | (Cliente.documento.ilike(busqueda))
            | (Cliente.direccion.ilike(busqueda))
        )

    clientes = query.order_by(Cliente.nombre.asc()).all()

    if filtro == "deudores":
        clientes = [c for c in clientes if c.deuda_total > 0]
    elif filtro == "aldia":
        clientes = [c for c in clientes if c.deuda_total == 0]

    total_deuda_clientes = round(sum(c.deuda_total for c in clientes), 2)

    return templates.TemplateResponse(
        request=request,
        name="clientes/index.html",
        context={
            "pagina_activa": "clientes",
            "clientes": clientes,
            "q": q,
            "filtro": filtro,
            "total_deuda_clientes": total_deuda_clientes,
        },
    )


@router.post("/crear")
def crear_cliente(
    nombre: str = Form(...),
    documento: str = Form(""),
    telefono: str = Form(""),
    direccion: str = Form(""),
    tipo_cliente: str = Form("Frecuente"),
    cupo_credito: float = Form(500000.0),
    notas: str = Form(""),
    origen: str = Form("/clientes"),
    db: Session = Depends(get_db),
):
    nombre_limpio = nombre.strip()
    if len(nombre_limpio) < 2:
        return redirect_con_mensaje(origen, "El nombre del cliente debe tener al menos 2 letras.", "error")

    nuevo = Cliente(
        nombre=nombre_limpio,
        documento=documento.strip(),
        telefono=telefono.strip(),
        direccion=direccion.strip(),
        tipo_cliente=tipo_cliente,
        cupo_credito=max(float(cupo_credito or 0.0), 0.0),
        notas=notas.strip(),
        activo=True,
    )
    db.add(nuevo)
    db.commit()
    return redirect_con_mensaje(origen, f"Cliente '{nuevo.nombre}' creado exitosamente.", "exito")


@router.post("/{cliente_id}/editar")
def editar_cliente(
    cliente_id: int,
    nombre: str = Form(...),
    documento: str = Form(""),
    telefono: str = Form(""),
    direccion: str = Form(""),
    tipo_cliente: str = Form("Frecuente"),
    cupo_credito: float = Form(500000.0),
    notas: str = Form(""),
    db: Session = Depends(get_db),
):
    cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not cliente:
        return redirect_con_mensaje("/clientes", "Cliente no encontrado.", "error")

    cliente.nombre = nombre.strip()
    cliente.documento = documento.strip()
    cliente.telefono = telefono.strip()
    cliente.direccion = direccion.strip()
    cliente.tipo_cliente = tipo_cliente
    cliente.cupo_credito = max(float(cupo_credito or 0.0), 0.0)
    cliente.notas = notas.strip()
    db.commit()
    return redirect_con_mensaje("/clientes", f"Datos de '{cliente.nombre}' actualizados.", "exito")


@router.post("/{cliente_id}/eliminar")
def eliminar_cliente(cliente_id: int, db: Session = Depends(get_db)):
    cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not cliente:
        return redirect_con_mensaje("/clientes", "Cliente no encontrado.", "error")

    if cliente.deuda_total > 0:
        return redirect_con_mensaje(
            "/clientes",
            f"No puedes eliminar a '{cliente.nombre}' porque tiene un saldo pendiente de cobro.",
            "error",
        )

    tiene_ventas = db.query(Venta).filter(Venta.cliente_id == cliente.id).count() > 0
    if tiene_ventas:
        cliente.activo = False
        db.commit()
        return redirect_con_mensaje("/clientes", f"Cliente '{cliente.nombre}' archivado correctamente.", "exito")

    db.delete(cliente)
    db.commit()
    return redirect_con_mensaje("/clientes", "Cliente eliminado correctamente.", "exito")
