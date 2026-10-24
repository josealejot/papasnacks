import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.cliente import Cliente
from app.models.producto import Producto
from app.services.capital_service import (
    registrar_venta,
    registrar_abono,
    registrar_entrada_inventario,
    registrar_gasto_operativo,
    obtener_resumen_capital,
)
from app.services.excel_generator import generar_excel_completo
from app.services.pdf_generator import generar_pdf_factura, generar_pdf_recibo_abono


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_flujo_completo_capital_snacks(db_session):
    # 1. Crear cliente y snack ($2.700 costo -> $4.000 venta)
    cliente = Cliente(nombre="Tienda La Bendición", telefono="3001112233", tipo_cliente="Tienda / Punto")
    snack = Producto(
        codigo="SNK-TEST",
        nombre="Papas Snack Tradicional",
        costo_compra=2700.0,
        precio_venta=4000.0,
        stock_actual=100,
        stock_minimo=15,
    )
    db_session.add_all([cliente, snack])
    db_session.commit()

    assert snack.ganancia_unitaria == 1300.0
    assert snack.margen_porcentaje == 32.5

    # 2. Registrar venta de 10 unidades ($40.000 total, utilidad $13.000)
    # Pago mixto inicial: $15.000 Efectivo + $10.000 Transferencia = $25.000 pagado, $15.000 deuda
    venta = registrar_venta(
        db=db_session,
        cliente_id=cliente.id,
        items=[{"producto_id": snack.id, "cantidad": 10, "precio_unitario": 4000.0}],
        pagado_efectivo=15000.0,
        pagado_transferencia=10000.0,
        referencia_transferencia="Nequi",
    )

    assert venta.total_unidades == 10
    assert venta.subtotal_costo == 27000.0
    assert venta.total_venta == 40000.0
    assert venta.utilidad_bruta == 13000.0
    assert venta.monto_pagado == 25000.0
    assert venta.saldo_pendiente == 15000.0
    assert venta.estado == "PARCIAL"
    assert snack.stock_actual == 90

    # 3. Validar Regla de Oro: No permitir abono mayor a la deuda pendiente ($15.000)
    with pytest.raises(ValueError, match="supera la deuda pendiente"):
        registrar_abono(
            db=db_session,
            venta_id=venta.id,
            monto_efectivo=10000.0,
            monto_transferencia=6000.0,  # $16.000 > $15.000
        )

    # 4. Registrar abono mixto válido que liquida la deuda ($5.000 Efectivo + $10.000 Transferencia)
    tx_abono = registrar_abono(
        db=db_session,
        venta_id=venta.id,
        monto_efectivo=5000.0,
        monto_transferencia=10000.0,
        entidad_transferencia="Bancolombia",
    )
    assert tx_abono.monto_total == 15000.0
    assert venta.saldo_pendiente == 0.0
    assert venta.estado == "PAGADO"
    assert venta.pagado_efectivo == 20000.0
    assert venta.pagado_transferencia == 20000.0

    # 5. Registrar gasto operativo de transporte por $3.000 en efectivo
    registrar_gasto_operativo(
        db=db_session,
        categoria="FLETE_TRANSPORTE",
        descripcion="Domicilio entrega pedido",
        monto_total=3000.0,
        pagado_efectivo=3000.0,
        pagado_transferencia=0.0,
    )

    # 6. Verificar resumen de capital
    resumen = obtener_resumen_capital(db_session)
    assert resumen["caja_efectivo"] == 17000.0          # 20.000 recibidos - 3.000 gasto
    assert resumen["bancos_transferencia"] == 20000.0   # 20.000 recibidos por transferencia
    assert resumen["liquidez_total"] == 37000.0
    assert resumen["capital_en_la_calle"] == 0.0
    assert resumen["utilidad_bruta_ventas"] == 13000.0
    assert resumen["gastos_operativos"] == 3000.0
    assert resumen["utilidad_neta"] == 10000.0
    assert resumen["stock_total_unidades"] == 90
    assert resumen["capital_inventario_costo"] == 90 * 2700.0

    # 7. Verificar generación de Excel y PDFs en memoria
    excel_io = generar_excel_completo(db_session)
    assert excel_io.getbuffer().nbytes > 1000

    pdf_fac = generar_pdf_factura(venta)
    assert pdf_fac.getbuffer().nbytes > 500

    pdf_rec = generar_pdf_recibo_abono(tx_abono)
    assert pdf_rec.getbuffer().nbytes > 500


def test_endpoints_web_y_descargas():
    from fastapi.testclient import TestClient
    from app import app, inicializar_datos_semilla

    inicializar_datos_semilla()
    client = TestClient(app)

    # Verificar vistas principales HTML
    for ruta in ["/", "/ventas", "/cartera", "/inventario", "/clientes", "/reportes", "/health"]:
        resp = client.get(ruta)
        assert resp.status_code == 200

    # Crear una venta desde el formulario POS con pago mixto
    resp_venta = client.post(
        "/ventas/crear",
        data={
            "cliente_id": "1",
            "producto_id": ["1"],
            "cantidad": ["5"],
            "precio_unitario": ["4000"],
            "pagado_efectivo": "10000",
            "pagado_transferencia": "6000",
            "descuento": "0",
            "referencia_transferencia": "Nequi",
            "notas": "Prueba automatizada POS",
        },
        follow_redirects=True,
    )
    assert resp_venta.status_code == 200

    # Descargar reporte Excel
    resp_excel = client.get("/reportes/excel")
    assert resp_excel.status_code == 200
    assert "spreadsheetml" in resp_excel.headers["content-type"]

    # Descargar factura PDF
    resp_pdf = client.get("/reportes/factura/1/pdf")
    assert resp_pdf.status_code == 200
    assert resp_pdf.headers["content-type"] == "application/pdf"

