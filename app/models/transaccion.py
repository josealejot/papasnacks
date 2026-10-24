from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from app.database import Base


class Transaccion(Base):
    __tablename__ = "transacciones"

    id = Column(Integer, primary_key=True, index=True)
    codigo_recibo = Column(String(40), unique=True, nullable=True, index=True)
    fecha = Column(DateTime, default=datetime.now, nullable=False, index=True)

    # Tipos:
    # INGRESO_VENTA, ABONO_CARTERA, APORTE_CAPITAL,
    # EGRESO_GASTO, COMPRA_INVENTARIO,
    # TRASPASO_CAJA_A_BANCO, TRASPASO_BANCO_A_CAJA
    tipo = Column(String(40), nullable=False, index=True)
    canal = Column(String(30), nullable=False, default="EFECTIVO")  # EFECTIVO, TRANSFERENCIA, MIXTO

    # Valores positivos indican magnitud del movimiento; la dirección (ingreso/egreso) la define `tipo`
    monto_efectivo = Column(Float, nullable=False, default=0.0)
    monto_transferencia = Column(Float, nullable=False, default=0.0)
    monto_total = Column(Float, nullable=False, default=0.0)

    entidad_transferencia = Column(String(80), nullable=True, default="")  # Nequi, Daviplata, Bancolombia, etc.
    concepto = Column(String(250), nullable=False, default="")

    venta_id = Column(Integer, ForeignKey("ventas.id"), nullable=True, index=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=True, index=True)
    gasto_id = Column(Integer, ForeignKey("gastos.id"), nullable=True, index=True)

    anulada = Column(Boolean, default=False, nullable=False)

    venta = relationship("Venta", back_populates="transacciones")
    cliente = relationship("Cliente", back_populates="transacciones")
    gasto = relationship("Gasto", back_populates="transacciones")

    @property
    def es_ingreso(self) -> bool:
        return self.tipo in ("INGRESO_VENTA", "ABONO_CARTERA", "APORTE_CAPITAL")

    @property
    def es_egreso(self) -> bool:
        return self.tipo in ("EGRESO_GASTO", "COMPRA_INVENTARIO")
