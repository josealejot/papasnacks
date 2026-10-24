from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.cliente import Cliente
from app.models.producto import Producto, MovimientoInventario
from app.models.venta import Venta, DetalleVenta
from app.models.transaccion import Transaccion
from app.models.gasto import Gasto


def generar_numero_factura(db: Session) -> str:
    ultimo = db.query(Venta).order_by(Venta.id.desc()).first()
    siguiente_id = (ultimo.id + 1) if ultimo else 1
    return f"FAC-{siguiente_id:04d}"


def generar_codigo_recibo(db: Session) -> str:
    ultimo = db.query(Transaccion).order_by(Transaccion.id.desc()).first()
    siguiente_id = (ultimo.id + 1) if ultimo else 1
    return f"REC-{siguiente_id:04d}"


def determinar_canal_pago(efectivo: float, transferencia: float) -> str:
    if efectivo > 0 and transferencia > 0:
        return "MIXTO"
    elif transferencia > 0:
        return "TRANSFERENCIA"
    elif efectivo > 0:
        return "EFECTIVO"
    return "CREDITO"


def registrar_venta(
    db: Session,
    cliente_id: int,
    items: List[Dict[str, Any]],
    pagado_efectivo: float = 0.0,
    pagado_transferencia: float = 0.0,
    descuento: float = 0.0,
    referencia_transferencia: str = "",
    notas: str = "",
    permitir_sin_stock: bool = False,
) -> Venta:
    """
    Registra una venta completa de snacks, descuenta inventario, calcula costo ($2.700 base)
    y utilidad ($1.300 base por unidad), registra el ingreso mixto (Efectivo / Transferencia)
    y deja cualquier excedente como saldo pendiente en Cartera.
    """
    cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not cliente:
        raise ValueError("El cliente seleccionado no existe.")

    if not items:
        raise ValueError("Debes agregar al menos un producto a la venta.")

    pagado_efectivo = round(max(float(pagado_efectivo or 0.0), 0.0), 2)
    pagado_transferencia = round(max(float(pagado_transferencia or 0.0), 0.0), 2)
    descuento = round(max(float(descuento or 0.0), 0.0), 2)

    total_unidades = 0
    subtotal_costo = 0.0
    subtotal_venta_bruto = 0.0
    detalles_a_crear: List[DetalleVenta] = []
    movimientos_stock: List[tuple[Producto, int]] = []

    for item in items:
        prod_id = int(item["producto_id"])
        cantidad = int(item["cantidad"])
        if cantidad <= 0:
            continue

        producto = db.query(Producto).filter(Producto.id == prod_id).first()
        if not producto:
            raise ValueError(f"Producto con ID {prod_id} no encontrado.")

        if not permitir_sin_stock and producto.stock_actual < cantidad:
            raise ValueError(
                f"Stock insuficiente para '{producto.nombre}'. "
                f"Disponible: {producto.stock_actual} unidades, solicitado: {cantidad}."
            )

        precio_unit = float(item.get("precio_unitario") or producto.precio_venta)
        costo_unit = float(producto.costo_compra)

        linea_costo = round(cantidad * costo_unit, 2)
        linea_venta = round(cantidad * precio_unit, 2)
        linea_utilidad = round(linea_venta - linea_costo, 2)

        total_unidades += cantidad
        subtotal_costo += linea_costo
        subtotal_venta_bruto += linea_venta

        detalles_a_crear.append(
            DetalleVenta(
                producto_id=producto.id,
                nombre_producto=producto.nombre,
                cantidad=cantidad,
                costo_unitario=costo_unit,
                precio_unitario=precio_unit,
                subtotal_costo=linea_costo,
                subtotal_venta=linea_venta,
                utilidad_linea=linea_utilidad,
            )
        )
        movimientos_stock.append((producto, cantidad))

    if total_unidades <= 0:
        raise ValueError("La cantidad total de unidades a vender debe ser mayor a cero.")

    total_venta = round(max(subtotal_venta_bruto - descuento, 0.0), 2)
    utilidad_bruta = round(total_venta - subtotal_costo, 2)

    monto_pagado = round(pagado_efectivo + pagado_transferencia, 2)
    if monto_pagado > total_venta + 0.01:
        raise ValueError(
            f"El pago total ($ {monto_pagado:,.0f}) no puede ser mayor al total de la venta ($ {total_venta:,.0f})."
        )

    saldo_pendiente = round(max(total_venta - monto_pagado, 0.0), 2)

    if saldo_pendiente == 0:
        estado = "PAGADO"
    elif monto_pagado > 0:
        estado = "PARCIAL"
    else:
        estado = "PENDIENTE"

    metodo_pago_inicial = determinar_canal_pago(pagado_efectivo, pagado_transferencia)
    numero_factura = generar_numero_factura(db)

    venta = Venta(
        numero_factura=numero_factura,
        cliente_id=cliente.id,
        fecha=datetime.now(),
        total_unidades=total_unidades,
        subtotal_costo=round(subtotal_costo, 2),
        descuento=descuento,
        total_venta=total_venta,
        utilidad_bruta=utilidad_bruta,
        pagado_efectivo=pagado_efectivo,
        pagado_transferencia=pagado_transferencia,
        monto_pagado=monto_pagado,
        saldo_pendiente=saldo_pendiente,
        metodo_pago_inicial=metodo_pago_inicial,
        referencia_transferencia=referencia_transferencia.strip() if referencia_transferencia else "",
        estado=estado,
        notas=notas.strip() if notas else "",
    )
    db.add(venta)
    db.flush()

    for det in detalles_a_crear:
        det.venta_id = venta.id
        db.add(det)

    # Descontar stock y registrar kardex de inventario
    for producto, cantidad in movimientos_stock:
        producto.stock_actual -= cantidad
        mov = MovimientoInventario(
            producto_id=producto.id,
            tipo="VENTA",
            cantidad=cantidad,
            stock_resultante=producto.stock_actual,
            costo_unitario=producto.costo_compra,
            costo_total=round(cantidad * producto.costo_compra, 2),
            proveedor=cliente.nombre,
            metodo_pago=metodo_pago_inicial,
            monto_efectivo=pagado_efectivo,
            monto_transferencia=pagado_transferencia,
            observacion=f"Venta según factura {numero_factura}",
            fecha=datetime.now(),
        )
        db.add(mov)

    # Si hubo pago inicial (efectivo y/o transferencia), crear transacción de caja/bancos
    if monto_pagado > 0:
        recibo = generar_codigo_recibo(db)
        tx = Transaccion(
            codigo_recibo=recibo,
            fecha=datetime.now(),
            tipo="INGRESO_VENTA",
            canal=metodo_pago_inicial,
            monto_efectivo=pagado_efectivo,
            monto_transferencia=pagado_transferencia,
            monto_total=monto_pagado,
            entidad_transferencia=referencia_transferencia.strip() if referencia_transferencia else "Transferencia",
            concepto=f"Pago inicial Factura {numero_factura} - {cliente.nombre}",
            venta_id=venta.id,
            cliente_id=cliente.id,
        )
        db.add(tx)

    db.commit()
    db.refresh(venta)
    return venta


def registrar_abono(
    db: Session,
    venta_id: int,
    monto_efectivo: float = 0.0,
    monto_transferencia: float = 0.0,
    entidad_transferencia: str = "Transferencia",
    concepto: str = "",
) -> Transaccion:
    """
    Registra un abono parcial o pago total sobre una factura con saldo pendiente.
    Cumple la regla de oro: nunca permite abonar más de la deuda pendiente.
    Soporta pago en Efectivo, Transferencia o Mixto.
    """
    venta = db.query(Venta).filter(Venta.id == venta_id).first()
    if not venta:
        raise ValueError("La factura indicada no existe.")

    if venta.estado == "ANULADA":
        raise ValueError("No se pueden registrar abonos en una factura anulada.")

    if venta.saldo_pendiente <= 0:
        raise ValueError(f"La factura {venta.numero_factura} ya se encuentra totalmente pagada.")

    monto_efectivo = round(max(float(monto_efectivo or 0.0), 0.0), 2)
    monto_transferencia = round(max(float(monto_transferencia or 0.0), 0.0), 2)
    monto_abono = round(monto_efectivo + monto_transferencia, 2)

    if monto_abono <= 0:
        raise ValueError("El monto del abono debe ser mayor a $ 0.")

    if monto_abono > venta.saldo_pendiente + 0.01:
        raise ValueError(
            f"El abono ($ {monto_abono:,.0f}) supera la deuda pendiente actual ($ {venta.saldo_pendiente:,.0f})."
        )

    venta.pagado_efectivo = round(venta.pagado_efectivo + monto_efectivo, 2)
    venta.pagado_transferencia = round(venta.pagado_transferencia + monto_transferencia, 2)
    venta.monto_pagado = round(venta.pagado_efectivo + venta.pagado_transferencia, 2)
    venta.saldo_pendiente = round(max(venta.total_venta - venta.monto_pagado, 0.0), 2)

    if venta.saldo_pendiente == 0:
        venta.estado = "PAGADO"
    else:
        venta.estado = "PARCIAL"

    canal = determinar_canal_pago(monto_efectivo, monto_transferencia)
    recibo = generar_codigo_recibo(db)
    texto_concepto = (
        concepto.strip()
        if concepto and concepto.strip()
        else f"Abono a Factura {venta.numero_factura} ({venta.cliente.nombre})"
    )

    tx = Transaccion(
        codigo_recibo=recibo,
        fecha=datetime.now(),
        tipo="ABONO_CARTERA",
        canal=canal,
        monto_efectivo=monto_efectivo,
        monto_transferencia=monto_transferencia,
        monto_total=monto_abono,
        entidad_transferencia=entidad_transferencia.strip() if entidad_transferencia else "",
        concepto=texto_concepto,
        venta_id=venta.id,
        cliente_id=venta.cliente_id,
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return tx


def anular_venta(db: Session, venta_id: int) -> Venta:
    """Anula una factura, devuelve las unidades al stock y anula sus transacciones."""
    venta = db.query(Venta).filter(Venta.id == venta_id).first()
    if not venta:
        raise ValueError("Factura no encontrada.")
    if venta.estado == "ANULADA":
        raise ValueError("Esta factura ya fue anulada.")

    for det in venta.detalles:
        producto = db.query(Producto).filter(Producto.id == det.producto_id).first()
        if producto:
            producto.stock_actual += det.cantidad
            mov = MovimientoInventario(
                producto_id=producto.id,
                tipo="ANULACION_VENTA",
                cantidad=det.cantidad,
                stock_resultante=producto.stock_actual,
                costo_unitario=det.costo_unitario,
                costo_total=det.subtotal_costo,
                proveedor=venta.cliente.nombre if venta.cliente else "",
                metodo_pago="N/A",
                observacion=f"Reintegro por anulación de {venta.numero_factura}",
                fecha=datetime.now(),
            )
            db.add(mov)

    for tx in venta.transacciones:
        tx.anulada = True

    venta.estado = "ANULADA"
    venta.saldo_pendiente = 0.0
    db.commit()
    db.refresh(venta)
    return venta


def registrar_entrada_inventario(
    db: Session,
    producto_id: int,
    cantidad: int,
    costo_unitario: float = 2700.0,
    pagado_efectivo: float = 0.0,
    pagado_transferencia: float = 0.0,
    proveedor: str = "Proveedor de Snacks",
    observacion: str = "",
    afectar_caja: bool = True,
) -> MovimientoInventario:
    """
    Registra la compra/entrada de un lote de snacks al inventario (por defecto a $2.700 unidad)
    y opcionalmente descuenta el pago de Caja (Efectivo) y/o Bancos (Transferencia).
    """
    producto = db.query(Producto).filter(Producto.id == producto_id).first()
    if not producto:
        raise ValueError("El producto seleccionado no existe.")
    if cantidad <= 0:
        raise ValueError("La cantidad de unidades a ingresar debe ser mayor a 0.")

    costo_unitario = round(max(float(costo_unitario), 0.0), 2)
    costo_total = round(cantidad * costo_unitario, 2)

    pagado_efectivo = round(max(float(pagado_efectivo or 0.0), 0.0), 2)
    pagado_transferencia = round(max(float(pagado_transferencia or 0.0), 0.0), 2)
    total_pagado = round(pagado_efectivo + pagado_transferencia, 2)

    if total_pagado > costo_total + 0.01:
        raise ValueError(
            f"El pago ($ {total_pagado:,.0f}) no puede superar el costo total del lote ($ {costo_total:,.0f})."
        )

    producto.stock_actual += cantidad
    producto.costo_compra = costo_unitario
    canal = determinar_canal_pago(pagado_efectivo, pagado_transferencia)

    mov = MovimientoInventario(
        producto_id=producto.id,
        tipo="ENTRADA_PROVEEDOR",
        cantidad=cantidad,
        stock_resultante=producto.stock_actual,
        costo_unitario=costo_unitario,
        costo_total=costo_total,
        proveedor=proveedor.strip() if proveedor else "Proveedor Principal",
        metodo_pago=canal,
        monto_efectivo=pagado_efectivo,
        monto_transferencia=pagado_transferencia,
        observacion=observacion.strip() if observacion else f"Compra de {cantidad} unds a $ {costo_unitario:,.0f}",
        fecha=datetime.now(),
    )
    db.add(mov)

    if afectar_caja and costo_total > 0:
        saldo_por_pagar = round(max(costo_total - total_pagado, 0.0), 2)
        estado_gasto = "PAGADO" if saldo_por_pagar == 0 else ("PARCIAL" if total_pagado > 0 else "PENDIENTE")
        gasto = Gasto(
            fecha=datetime.now(),
            categoria="COMPRA_PROVEEDOR",
            descripcion=f"Compra lote: {cantidad}x {producto.nombre} ($ {costo_unitario:,.0f} c/u)",
            proveedor=proveedor.strip() if proveedor else "Proveedor Principal",
            monto_total=costo_total,
            pagado_efectivo=pagado_efectivo,
            pagado_transferencia=pagado_transferencia,
            saldo_por_pagar=saldo_por_pagar,
            metodo_pago=canal,
            estado=estado_gasto,
            es_compra_inventario=True,
        )
        db.add(gasto)
        db.flush()

        if total_pagado > 0:
            tx = Transaccion(
                codigo_recibo=generar_codigo_recibo(db),
                fecha=datetime.now(),
                tipo="COMPRA_INVENTARIO",
                canal=canal,
                monto_efectivo=pagado_efectivo,
                monto_transferencia=pagado_transferencia,
                monto_total=total_pagado,
                entidad_transferencia="Transferencia Proveedor" if pagado_transferencia > 0 else "Caja Efectivo",
                concepto=f"Pago proveedor: {cantidad} unds {producto.nombre}",
                gasto_id=gasto.id,
            )
            db.add(tx)

    db.commit()
    db.refresh(mov)
    return mov


def registrar_gasto_operativo(
    db: Session,
    categoria: str,
    descripcion: str,
    monto_total: float,
    pagado_efectivo: float = 0.0,
    pagado_transferencia: float = 0.0,
    proveedor: str = "",
) -> Gasto:
    """Registra un gasto operativo (fletes, bolsas, transporte, caja menor) y descuenta de caja/bancos."""
    monto_total = round(max(float(monto_total or 0.0), 0.0), 2)
    if monto_total <= 0:
        raise ValueError("El monto del gasto debe ser mayor a $ 0.")

    pagado_efectivo = round(max(float(pagado_efectivo or 0.0), 0.0), 2)
    pagado_transferencia = round(max(float(pagado_transferencia or 0.0), 0.0), 2)
    total_pagado = round(pagado_efectivo + pagado_transferencia, 2)

    if total_pagado > monto_total + 0.01:
        raise ValueError("El monto pagado no puede superar el valor total del gasto.")

    saldo_por_pagar = round(max(monto_total - total_pagado, 0.0), 2)
    estado = "PAGADO" if saldo_por_pagar == 0 else ("PARCIAL" if total_pagado > 0 else "PENDIENTE")
    canal = determinar_canal_pago(pagado_efectivo, pagado_transferencia)

    es_inventario = categoria == "COMPRA_PROVEEDOR"

    gasto = Gasto(
        fecha=datetime.now(),
        categoria=categoria,
        descripcion=descripcion.strip(),
        proveedor=proveedor.strip() if proveedor else "",
        monto_total=monto_total,
        pagado_efectivo=pagado_efectivo,
        pagado_transferencia=pagado_transferencia,
        saldo_por_pagar=saldo_por_pagar,
        metodo_pago=canal,
        estado=estado,
        es_compra_inventario=es_inventario,
    )
    db.add(gasto)
    db.flush()

    if total_pagado > 0:
        tx = Transaccion(
            codigo_recibo=generar_codigo_recibo(db),
            fecha=datetime.now(),
            tipo="COMPRA_INVENTARIO" if es_inventario else "EGRESO_GASTO",
            canal=canal,
            monto_efectivo=pagado_efectivo,
            monto_transferencia=pagado_transferencia,
            monto_total=total_pagado,
            entidad_transferencia="Transferencia" if pagado_transferencia > 0 else "Efectivo",
            concepto=f"Gasto ({categoria}): {descripcion.strip()}",
            gasto_id=gasto.id,
        )
        db.add(tx)

    db.commit()
    db.refresh(gasto)
    return gasto


def registrar_movimiento_capital(
    db: Session,
    tipo: str,
    monto_efectivo: float = 0.0,
    monto_transferencia: float = 0.0,
    concepto: str = "",
    entidad_transferencia: str = "Nequi / Bancolombia",
) -> Transaccion:
    """
    Permite:
    - APORTE_CAPITAL: Inyectar saldo inicial o capital extra en Efectivo y/o Transferencia.
    - TRASPASO_CAJA_A_BANCO: Pasar dinero de Efectivo a Transferencia/Banco.
    - TRASPASO_BANCO_A_CAJA: Retirar dinero de Transferencia/Banco a Efectivo.
    """
    monto_efectivo = round(max(float(monto_efectivo or 0.0), 0.0), 2)
    monto_transferencia = round(max(float(monto_transferencia or 0.0), 0.0), 2)
    monto_total = round(monto_efectivo + monto_transferencia, 2)

    if monto_total <= 0:
        raise ValueError("El monto del movimiento de capital debe ser mayor a $ 0.")

    canal = determinar_canal_pago(monto_efectivo, monto_transferencia)
    tx = Transaccion(
        codigo_recibo=generar_codigo_recibo(db),
        fecha=datetime.now(),
        tipo=tipo,
        canal=canal,
        monto_efectivo=monto_efectivo,
        monto_transferencia=monto_transferencia,
        monto_total=monto_total,
        entidad_transferencia=entidad_transferencia,
        concepto=concepto.strip() or f"Movimiento de capital ({tipo})",
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return tx


def obtener_resumen_capital(db: Session) -> Dict[str, Any]:
    """
    Calcula en tiempo real la radiografía financiera completa de Isaías Papas:
    - Caja en Efectivo vs Dinero en Transferencias Electrónicas
    - Capital en la calle (Cartera por cobrar a clientes)
    - Capital invertido en Inventario ($2.700/und) y valor de venta ($4.000/und)
    - Utilidad Bruta ($1.300/und base), Gastos Operativos y Utilidad Neta
    - Patrimonio Total del Negocio
    """
    transacciones = db.query(Transaccion).filter(Transaccion.anulada == False).all()

    caja_efectivo = 0.0
    bancos_transferencia = 0.0
    ingresos_efectivo_total = 0.0
    ingresos_transferencia_total = 0.0
    egresos_efectivo_total = 0.0
    egresos_transferencia_total = 0.0

    for tx in transacciones:
        if tx.tipo in ("INGRESO_VENTA", "ABONO_CARTERA", "APORTE_CAPITAL"):
            caja_efectivo += tx.monto_efectivo
            bancos_transferencia += tx.monto_transferencia
            if tx.tipo in ("INGRESO_VENTA", "ABONO_CARTERA"):
                ingresos_efectivo_total += tx.monto_efectivo
                ingresos_transferencia_total += tx.monto_transferencia
        elif tx.tipo in ("EGRESO_GASTO", "COMPRA_INVENTARIO"):
            caja_efectivo -= tx.monto_efectivo
            bancos_transferencia -= tx.monto_transferencia
            egresos_efectivo_total += tx.monto_efectivo
            egresos_transferencia_total += tx.monto_transferencia
        elif tx.tipo == "TRASPASO_CAJA_A_BANCO":
            monto = tx.monto_total
            caja_efectivo -= monto
            bancos_transferencia += monto
        elif tx.tipo == "TRASPASO_BANCO_A_CAJA":
            monto = tx.monto_total
            bancos_transferencia -= monto
            caja_efectivo += monto

    liquidez_total = round(caja_efectivo + bancos_transferencia, 2)

    # Ventas activas
    ventas_activas = db.query(Venta).filter(Venta.estado != "ANULADA").all()
    ventas_totales = round(sum(v.total_venta for v in ventas_activas), 2)
    unidades_vendidas = sum(v.total_unidades for v in ventas_activas)
    costo_mercancia_vendida = round(sum(v.subtotal_costo for v in ventas_activas), 2)
    utilidad_bruta_ventas = round(sum(v.utilidad_bruta for v in ventas_activas), 2)
    recaudo_total_ventas = round(sum(v.monto_pagado for v in ventas_activas), 2)
    capital_en_la_calle = round(sum(v.saldo_pendiente for v in ventas_activas), 2)

    utilidad_realizada = round(sum(v.utilidad_realizada for v in ventas_activas), 2)
    utilidad_por_cobrar = round(max(utilidad_bruta_ventas - utilidad_realizada, 0.0), 2)

    # Conteo por estado de facturas
    facturas_pagadas = sum(1 for v in ventas_activas if v.estado == "PAGADO")
    facturas_parciales = sum(1 for v in ventas_activas if v.estado == "PARCIAL")
    facturas_pendientes = sum(1 for v in ventas_activas if v.estado == "PENDIENTE")

    # Inventario
    productos = db.query(Producto).filter(Producto.activo == True).all()
    stock_total_unidades = sum(max(p.stock_actual, 0) for p in productos)
    capital_inventario_costo = round(sum(p.valor_inventario_costo for p in productos), 2)
    capital_inventario_venta = round(sum(p.valor_inventario_venta for p in productos), 2)
    utilidad_potencial_inventario = round(sum(p.utilidad_potencial_stock for p in productos), 2)
    productos_bajo_stock = [p for p in productos if p.bajo_stock]

    # Gastos operativos vs Compras de inventario
    gastos = db.query(Gasto).all()
    gastos_operativos = round(sum(g.monto_total for g in gastos if not g.es_compra_inventario), 2)
    compras_inventario = round(sum(g.monto_total for g in gastos if g.es_compra_inventario), 2)
    cuentas_por_pagar_proveedores = round(sum(g.saldo_por_pagar for g in gastos if g.saldo_por_pagar > 0), 2)

    utilidad_neta = round(utilidad_bruta_ventas - gastos_operativos, 2)
    margen_bruto_pct = round((utilidad_bruta_ventas / ventas_totales) * 100, 1) if ventas_totales > 0 else 32.5
    margen_neto_pct = round((utilidad_neta / ventas_totales) * 100, 1) if ventas_totales > 0 else 0.0

    # Patrimonio Total = Liquidez disponible + Cartera por cobrar + Inventario al costo - Cuentas por pagar
    patrimonio_total = round(
        liquidez_total + capital_en_la_calle + capital_inventario_costo - cuentas_por_pagar_proveedores, 2
    )

    # Serie de últimos 7 días para gráfica
    hoy = datetime.now().date()
    serie_diaria = []
    dias_es = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
    for i in range(6, -1, -1):
        dia = hoy - timedelta(days=i)
        ventas_dia = [v for v in ventas_activas if v.fecha.date() == dia]
        monto_dia = round(sum(v.total_venta for v in ventas_dia), 2)
        utilidad_dia = round(sum(v.utilidad_bruta for v in ventas_dia), 2)
        unidades_dia = sum(v.total_unidades for v in ventas_dia)
        serie_diaria.append(
            {
                "fecha": dia.strftime("%d/%m"),
                "etiqueta": f"{dias_es[dia.weekday()]} {dia.strftime('%d')}",
                "ventas": monto_dia,
                "utilidad": utilidad_dia,
                "unidades": unidades_dia,
            }
        )

    max_venta_diaria = max((d["ventas"] for d in serie_diaria), default=1.0) or 1.0
    for d in serie_diaria:
        d["altura_pct"] = max(int(round((d["ventas"] / max_venta_diaria) * 100)), 6) if d["ventas"] > 0 else 4

    return {
        "caja_efectivo": round(caja_efectivo, 2),
        "bancos_transferencia": round(bancos_transferencia, 2),
        "liquidez_total": liquidez_total,
        "ingresos_efectivo_total": round(ingresos_efectivo_total, 2),
        "ingresos_transferencia_total": round(ingresos_transferencia_total, 2),
        "egresos_efectivo_total": round(egresos_efectivo_total, 2),
        "egresos_transferencia_total": round(egresos_transferencia_total, 2),
        "capital_en_la_calle": capital_en_la_calle,
        "recaudo_total_ventas": recaudo_total_ventas,
        "ventas_totales": ventas_totales,
        "unidades_vendidas": unidades_vendidas,
        "costo_mercancia_vendida": costo_mercancia_vendida,
        "utilidad_bruta_ventas": utilidad_bruta_ventas,
        "utilidad_realizada": utilidad_realizada,
        "utilidad_por_cobrar": utilidad_por_cobrar,
        "gastos_operativos": gastos_operativos,
        "compras_inventario": compras_inventario,
        "cuentas_por_pagar_proveedores": cuentas_por_pagar_proveedores,
        "utilidad_neta": utilidad_neta,
        "margen_bruto_pct": margen_bruto_pct,
        "margen_neto_pct": margen_neto_pct,
        "stock_total_unidades": stock_total_unidades,
        "capital_inventario_costo": capital_inventario_costo,
        "capital_inventario_venta": capital_inventario_venta,
        "utilidad_potencial_inventario": utilidad_potencial_inventario,
        "patrimonio_total": patrimonio_total,
        "facturas_pagadas": facturas_pagadas,
        "facturas_parciales": facturas_parciales,
        "facturas_pendientes": facturas_pendientes,
        "total_facturas": len(ventas_activas),
        "productos_bajo_stock": productos_bajo_stock,
        "serie_diaria": serie_diaria,
    }
