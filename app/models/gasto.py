from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String
from sqlalchemy.orm import relationship
from app.database import Base


class Gasto(Base):
    __tablename__ = "gastos"

    id = Column(Integer, primary_key=True, index=True)
    fecha = Column(DateTime, default=datetime.now, nullable=False, index=True)
    # Categorías: COMPRA_PROVEEDOR, FLETE_TRANSPORTE, EMPAQUES_BOLSAS, SERVICIOS_OPERACION, CAJA_MENOR, OTROS
    categoria = Column(String(50), nullable=False, default="FLETE_TRANSPORTE", index=True)
    descripcion = Column(String(250), nullable=False)
    proveedor = Column(String(120), nullable=True, default="")

    monto_total = Column(Float, nullable=False, default=0.0)
    pagado_efectivo = Column(Float, nullable=False, default=0.0)
    pagado_transferencia = Column(Float, nullable=False, default=0.0)
    saldo_por_pagar = Column(Float, nullable=False, default=0.0)

    metodo_pago = Column(String(40), nullable=False, default="EFECTIVO")  # EFECTIVO, TRANSFERENCIA, MIXTO, CREDITO
    estado = Column(String(30), nullable=False, default="PAGADO")  # PAGADO, PARCIAL, PENDIENTE
    es_compra_inventario = Column(Boolean, default=False, nullable=False)

    transacciones = relationship("Transaccion", back_populates="gasto", cascade="all, delete-orphan")
