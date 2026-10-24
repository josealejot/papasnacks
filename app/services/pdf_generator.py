from io import BytesIO
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

from app.config import settings, format_cop
from app.models.venta import Venta
from app.models.transaccion import Transaccion
from app.models.cliente import Cliente


def generar_pdf_factura(venta: Venta) -> BytesIO:
    """Genera una Factura / Comprobante de Venta PDF membretado y listo para imprimir o enviar por WhatsApp."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
        title=f"Factura {venta.numero_factura} - {settings.BUSINESS_NAME}",
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "TitleBrand",
        parent=styles["Heading1"],
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#0F172A"),
        spaceAfter=2,
    )
    sub_style = ParagraphStyle(
        "SubBrand",
        parent=styles["Normal"],
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor("#475569"),
    )
    right_style = ParagraphStyle(
        "RightInfo",
        parent=styles["Normal"],
        fontSize=10,
        leading=14,
        alignment=2,
        textColor=colors.HexColor("#1E293B"),
    )
    section_title = ParagraphStyle(
        "SectionTitle",
        parent=styles["Heading3"],
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#0F172A"),
        spaceBefore=8,
        spaceAfter=4,
    )

    elementos = []

    # Color semántico de estado
    if venta.estado == "PAGADO":
        estado_label = "PAGADO TOTAL"
        color_estado = colors.HexColor("#16A34A")
    elif venta.estado == "PARCIAL":
        estado_label = "ABONO PARCIAL (SALDO PENDIENTE)"
        color_estado = colors.HexColor("#D97706")
    elif venta.estado == "ANULADA":
        estado_label = "FACTURA ANULADA"
        color_estado = colors.HexColor("#64748B")
    else:
        estado_label = "CRÉDITO / PENDIENTE DE PAGO"
        color_estado = colors.HexColor("#DC2626")

    # Encabezado membretado
    izquierda = [
        Paragraph(f"<b>{settings.BUSINESS_NAME}</b>", title_style),
        Paragraph("Comercialización y Distribución de Snacks de Papa", sub_style),
        Paragraph(f"<b>NIT / CC:</b> {settings.BUSINESS_NIT} | <b>Tel:</b> {settings.BUSINESS_PHONE}", sub_style),
        Paragraph(f"{settings.BUSINESS_CITY}", sub_style),
    ]
    derecha = [
        Paragraph(f"<font size=14><b>FACTURA DE VENTA</b></font>", right_style),
        Paragraph(f"<font size=13 color='#2563EB'><b>N° {venta.numero_factura}</b></font>", right_style),
        Paragraph(f"<b>Fecha:</b> {venta.fecha.strftime('%d/%m/%Y %H:%M')}", right_style),
        Paragraph(f"<b>Estado:</b> <font color='{color_estado.hexval()}'><b>{estado_label}</b></font>", right_style),
    ]

    header_table = Table([[izquierda, derecha]], colWidths=[105 * mm, 80 * mm])
    header_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("LINEBELOW", (0, 0), (-1, 0), 1.5, colors.HexColor("#E2E8F0")),
            ]
        )
    )
    elementos.append(header_table)
    elementos.append(Spacer(1, 5 * mm))

    # Datos del Cliente
    cliente_nombre = venta.cliente.nombre if venta.cliente else "Cliente Mostrador"
    cliente_doc = venta.cliente.documento if (venta.cliente and venta.cliente.documento) else "No registrado"
    cliente_tel = venta.cliente.telefono if (venta.cliente and venta.cliente.telefono) else "No registrado"
    cliente_dir = venta.cliente.direccion if (venta.cliente and venta.cliente.direccion) else "Entrega directa"

    info_cliente = [
        [
            Paragraph(f"<b>CLIENTE:</b> {cliente_nombre}", styles["Normal"]),
            Paragraph(f"<b>NIT / CC:</b> {cliente_doc}", styles["Normal"]),
        ],
        [
            Paragraph(f"<b>DIRECCIÓN:</b> {cliente_dir}", styles["Normal"]),
            Paragraph(f"<b>TELÉFONO:</b> {cliente_tel}", styles["Normal"]),
        ],
    ]
    tabla_cliente = Table(info_cliente, colWidths=[110 * mm, 75 * mm])
    tabla_cliente.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
                ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#CBD5E1")),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    elementos.append(tabla_cliente)
    elementos.append(Spacer(1, 6 * mm))

    # Tabla de Productos / Snacks
    datos_items = [["Ítem", "Descripción del Producto (Snack)", "Cantidad", "Precio Unit.", "Subtotal"]]
    for idx, det in enumerate(venta.detalles, start=1):
        datos_items.append(
            [
                str(idx),
                det.nombre_producto,
                f"{det.cantidad} unds",
                format_cop(det.precio_unitario),
                format_cop(det.subtotal_venta),
            ]
        )

    tabla_items = Table(datos_items, colWidths=[15 * mm, 85 * mm, 25 * mm, 30 * mm, 30 * mm])
    tabla_items.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 9.5),
                ("ALIGN", (0, 0), (0, -1), "CENTER"),
                ("ALIGN", (2, 0), (2, -1), "CENTER"),
                ("ALIGN", (3, 0), (-1, -1), "RIGHT"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    elementos.append(tabla_items)
    elementos.append(Spacer(1, 5 * mm))

    # Resumen de Pago Mixto (Efectivo + Transferencia + Saldo Pendiente)
    resumen_filas = [
        ["Total Unidades Entregadas:", f"{venta.total_unidades} unidades"],
    ]
    if venta.descuento > 0:
        resumen_filas.append(["Descuento Aplicado:", f"- {format_cop(venta.descuento)}"])

    resumen_filas.extend(
        [
            ["TOTAL FACTURA:", format_cop(venta.total_venta)],
            ["Pagado en Efectivo (Caja):", format_cop(venta.pagado_efectivo)],
            ["Pagado por Transferencia Electrónica:", format_cop(venta.pagado_transferencia)],
            ["TOTAL ABONADO / PAGADO:", format_cop(venta.monto_pagado)],
            ["SALDO PENDIENTE POR COBRAR:", format_cop(venta.saldo_pendiente)],
        ]
    )

    tabla_totales = Table(resumen_filas, colWidths=[65 * mm, 40 * mm], hAlign="RIGHT")
    tabla_totales.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("ALIGN", (0, 0), (0, -1), "LEFT"),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
                ("FONTNAME", (0, -2), (-1, -1), "Helvetica-Bold"),
                ("BACKGROUND", (0, -2), (-1, -2), colors.HexColor("#DCFCE7")),
                (
                    "BACKGROUND",
                    (0, -1),
                    (-1, -1),
                    colors.HexColor("#FEE2E2") if venta.saldo_pendiente > 0 else colors.HexColor("#DCFCE7"),
                ),
                (
                    "TEXTCOLOR",
                    (0, -1),
                    (-1, -1),
                    colors.HexColor("#991B1B") if venta.saldo_pendiente > 0 else colors.HexColor("#166534"),
                ),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    elementos.append(tabla_totales)

    # Historial de Pagos / Abonos de esta Factura
    pagos_activos = [tx for tx in venta.transacciones if not tx.anulada]
    if pagos_activos:
        elementos.append(Spacer(1, 5 * mm))
        elementos.append(Paragraph("Historial de Pagos y Abonos Registrados", section_title))
        filas_tx = [["Recibo", "Fecha", "Canal", "Efectivo", "Transferencia", "Total Abono"]]
        for tx in pagos_activos:
            filas_tx.append(
                [
                    tx.codigo_recibo or f"TX-{tx.id}",
                    tx.fecha.strftime("%d/%m/%Y %H:%M"),
                    tx.canal,
                    format_cop(tx.monto_efectivo),
                    format_cop(tx.monto_transferencia),
                    format_cop(tx.monto_total),
                ]
            )
        tabla_tx = Table(filas_tx, colWidths=[28 * mm, 35 * mm, 32 * mm, 30 * mm, 30 * mm, 30 * mm])
        tabla_tx.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#334155")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                    ("ALIGN", (3, 0), (-1, -1), "RIGHT"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        elementos.append(tabla_tx)

    if venta.notas:
        elementos.append(Spacer(1, 4 * mm))
        elementos.append(Paragraph(f"<b>Observaciones:</b> {venta.notas}", sub_style))

    elementos.append(Spacer(1, 8 * mm))
    elementos.append(
        Paragraph(
            f"Comprobante generado por <b>{settings.APP_NAME}</b> el {datetime.now().strftime('%d/%m/%Y %H:%M')}. ¡Gracias por su compra!",
            sub_style,
        )
    )

    doc.build(elementos)
    buffer.seek(0)
    return buffer


def generar_pdf_recibo_abono(tx: Transaccion) -> BytesIO:
    """Genera un Recibo de Caja / Comprobante de Abono PDF descargable."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title=f"Recibo {tx.codigo_recibo or tx.id} - {settings.BUSINESS_NAME}",
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "RecTitle",
        parent=styles["Heading1"],
        fontSize=16,
        textColor=colors.HexColor("#0F172A"),
    )

    elementos = []
    elementos.append(Paragraph(f"<b>{settings.BUSINESS_NAME}</b>", title_style))
    elementos.append(
        Paragraph(
            f"<b>RECIBO OFICIAL DE CAJA / ABONO N° {tx.codigo_recibo or tx.id}</b> | Fecha: {tx.fecha.strftime('%d/%m/%Y %H:%M')}",
            styles["Normal"],
        )
    )
    elementos.append(Spacer(1, 5 * mm))

    cliente_nombre = tx.cliente.nombre if tx.cliente else "Cliente General"
    factura_num = tx.venta.numero_factura if tx.venta else "N/A"
    saldo_restante = tx.venta.saldo_pendiente if tx.venta else 0.0

    filas = [
        ["Recibido de (Cliente):", cliente_nombre],
        ["Factura Asociada:", factura_num],
        ["Concepto:", tx.concepto],
        ["Modalidad de Pago:", tx.canal],
        ["Valor Recibido en Efectivo:", format_cop(tx.monto_efectivo)],
        ["Valor Recibido por Transferencia:", format_cop(tx.monto_transferencia)],
        ["TOTAL RECIBIDO EN ESTE ABONO:", format_cop(tx.monto_total)],
        ["SALDO PENDIENTE ACTUAL DE LA FACTURA:", format_cop(saldo_restante)],
    ]

    tabla = Table(filas, colWidths=[80 * mm, 95 * mm])
    tabla.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.6, colors.HexColor("#CBD5E1")),
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F8FAFC")),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTNAME", (0, -2), (-1, -1), "Helvetica-Bold"),
                ("BACKGROUND", (0, -2), (-1, -2), colors.HexColor("#DCFCE7")),
                (
                    "BACKGROUND",
                    (0, -1),
                    (-1, -1),
                    colors.HexColor("#FEF9C3") if saldo_restante > 0 else colors.HexColor("#DCFCE7"),
                ),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    elementos.append(tabla)
    elementos.append(Spacer(1, 10 * mm))
    elementos.append(Paragraph("___________________________________________", styles["Normal"]))
    elementos.append(Paragraph(f"Firma / Sello de Recibido - {settings.BUSINESS_NAME}", styles["Normal"]))

    doc.build(elementos)
    buffer.seek(0)
    return buffer
