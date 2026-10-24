from datetime import datetime
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.venta import Venta
from app.models.transaccion import Transaccion
from app.models.gasto import Gasto
from app.routes import templates, redirect_con_mensaje
from app.services.capital_service import obtener_resumen_capital
from app.services.excel_generator import generar_excel_completo
from app.services.pdf_generator import generar_pdf_factura, generar_pdf_recibo_abono

router = APIRouter(prefix="/reportes", tags=["Reportes"])


@router.get("", response_class=HTMLResponse)
def vista_reportes(request: Request, db: Session = Depends(get_db)):
    resumen = obtener_resumen_capital(db)
    ventas = db.query(Venta).filter(Venta.estado != "ANULADA").order_by(Venta.fecha.desc()).limit(15).all()
    transacciones = (
        db.query(Transaccion)
        .filter(Transaccion.anulada == False)
        .order_by(Transaccion.fecha.desc())
        .limit(20)
        .all()
    )
    gastos = db.query(Gasto).order_by(Gasto.fecha.desc()).limit(15).all()

    return templates.TemplateResponse(
        request=request,
        name="reportes/index.html",
        context={
            "pagina_activa": "reportes",
            "resumen": resumen,
            "ventas": ventas,
            "transacciones": transacciones,
            "gastos": gastos,
        },
    )


@router.get("/excel")
def descargar_reporte_excel(db: Session = Depends(get_db)):
    archivo_excel = generar_excel_completo(db)
    fecha_str = datetime.now().strftime("%Y%m%d_%H%M")
    filename = f"Isaias_Papas_Reporte_Capital_{fecha_str}.xlsx"
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return StreamingResponse(
        archivo_excel,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers,
    )


@router.get("/factura/{venta_id}/pdf")
def descargar_factura_pdf(venta_id: int, db: Session = Depends(get_db)):
    venta = db.query(Venta).filter(Venta.id == venta_id).first()
    if not venta:
        return redirect_con_mensaje("/ventas", "Factura no encontrada.", "error")

    pdf_buffer = generar_pdf_factura(venta)
    filename = f"Factura_{venta.numero_factura}_Isaias_Papas.pdf"
    headers = {"Content-Disposition": f'inline; filename="{filename}"'}
    return StreamingResponse(pdf_buffer, media_type="application/pdf", headers=headers)


@router.get("/recibo/{transaccion_id}/pdf")
def descargar_recibo_pdf(transaccion_id: int, db: Session = Depends(get_db)):
    tx = db.query(Transaccion).filter(Transaccion.id == transaccion_id).first()
    if not tx:
        return redirect_con_mensaje("/cartera", "Recibo no encontrado.", "error")

    pdf_buffer = generar_pdf_recibo_abono(tx)
    codigo = tx.codigo_recibo or f"REC-{tx.id}"
    filename = f"Recibo_{codigo}_Isaias_Papas.pdf"
    headers = {"Content-Disposition": f'inline; filename="{filename}"'}
    return StreamingResponse(pdf_buffer, media_type="application/pdf", headers=headers)
