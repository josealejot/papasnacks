from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import relationship
from app.database import Base


class Cliente(Base):
    __tablename__ = "clientes"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(150), nullable=False, index=True)
    documento = Column(String(50), nullable=True, default="")
    telefono = Column(String(50), nullable=True, default="")
    direccion = Column(String(200), nullable=True, default="")
    tipo_cliente = Column(String(50), nullable=False, default="Frecuente")  # Detal, Mayorista, Tienda, Frecuente
    cupo_credito = Column(Float, nullable=False, default=500000.0)
    notas = Column(Text, nullable=True, default="")
    activo = Column(Boolean, default=True, nullable=False)
    fecha_creacion = Column(DateTime, default=datetime.now, nullable=False)

    ventas = relationship("Venta", back_populates="cliente", cascade="all, delete-orphan")
    transacciones = relationship("Transaccion", back_populates="cliente")

    @property
    def deuda_total(self) -> float:
        if not self.ventas:
            return 0.0
        return round(
            sum(v.saldo_pendiente for v in self.ventas if v.estado != "ANULADA" and v.saldo_pendiente > 0),
            2,
        )

    @property
    def total_comprado(self) -> float:
        if not self.ventas:
            return 0.0
        return round(
            sum(v.total_venta for v in self.ventas if v.estado != "ANULADA"),
            2,
        )

    @property
    def facturas_pendientes_count(self) -> int:
        if not self.ventas:
            return 0
        return sum(1 for v in self.ventas if v.estado in ("PENDIENTE", "PARCIAL") and v.saldo_pendiente > 0)
