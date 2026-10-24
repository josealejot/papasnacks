from datetime import datetime
from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from app.database import Base


class Venta(Base):
    __tablename__ = "ventas"

    id = Column(Integer, primary_key=True, index=True)
    numero_factura = Column(String(40), unique=True, nullable=False, index=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False, index=True)
    fecha = Column(DateTime, default=datetime.now, nullable=False, index=True)

    total_unidades = Column(Integer, nullable=False, default=0)
    subtotal_costo = Column(Float, nullable=False, default=0.0)
    descuento = Column(Float, nullable=False, default=0.0)
    total_venta = Column(Float, nullable=False, default=0.0)
    utilidad_bruta = Column(Float, nullable=False, default=0.0)

    pagado_efectivo = Column(Float, nullable=False, default=0.0)
    pagado_transferencia = Column(Float, nullable=False, default=0.0)
    monto_pagado = Column(Float, nullable=False, default=0.0)
    saldo_pendiente = Column(Float, nullable=False, default=0.0)

    metodo_pago_inicial = Column(String(40), nullable=False, default="EFECTIVO")  # EFECTIVO, TRANSFERENCIA, MIXTO, CREDITO
    referencia_transferencia = Column(String(100), nullable=True, default="")
    estado = Column(String(30), nullable=False, default="PAGADO", index=True)  # PAGADO, PARCIAL, PENDIENTE, ANULADA
    notas = Column(Text, nullable=True, default="")

    cliente = relationship("Cliente", back_populates="ventas")
    detalles = relationship("DetalleVenta", back_populates="venta", cascade="all, delete-orphan")
    transacciones = relationship("Transaccion", back_populates="venta", cascade="all, delete-orphan")

    @property
    def porcentaje_pagado(self) -> float:
        if self.total_venta <= 0:
            return 100.0
        return round(min((self.monto_pagado / self.total_venta) * 100, 100.0), 1)

    @property
    def utilidad_realizada(self) -> float:
        """Utilidad proporcional efectivamente cobrada en caja/bancos."""
        if self.total_venta <= 0 or self.estado == "ANULADA":
            return 0.0
        proporcion = min(self.monto_pagado / self.total_venta, 1.0)
        return round(self.utilidad_bruta * proporcion, 2)


class DetalleVenta(Base):
    __tablename__ = "detalles_venta"

    id = Column(Integer, primary_key=True, index=True)
    venta_id = Column(Integer, ForeignKey("ventas.id"), nullable=False, index=True)
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=False, index=True)
    nombre_producto = Column(String(150), nullable=False)
    cantidad = Column(Integer, nullable=False, default=1)
    costo_unitario = Column(Float, nullable=False, default=2700.0)
    precio_unitario = Column(Float, nullable=False, default=4000.0)
    subtotal_costo = Column(Float, nullable=False, default=2700.0)
    subtotal_venta = Column(Float, nullable=False, default=4000.0)
    utilidad_linea = Column(Float, nullable=False, default=1300.0)

    venta = relationship("Venta", back_populates="detalles")
    producto = relationship("Producto", back_populates="detalles_venta")
