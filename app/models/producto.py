from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from app.database import Base


class Producto(Base):
    __tablename__ = "productos"

    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String(50), unique=True, nullable=False, index=True)
    nombre = Column(String(150), nullable=False, index=True)
    sabor = Column(String(80), nullable=True, default="Tradicional")
    presentacion = Column(String(80), nullable=False, default="Paquete Unidad")
    costo_compra = Column(Float, nullable=False, default=2700.0)
    precio_venta = Column(Float, nullable=False, default=4000.0)
    stock_actual = Column(Integer, nullable=False, default=0)
    stock_minimo = Column(Integer, nullable=False, default=20)
    activo = Column(Boolean, default=True, nullable=False)
    fecha_actualizacion = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)

    movimientos = relationship("MovimientoInventario", back_populates="producto", cascade="all, delete-orphan")
    detalles_venta = relationship("DetalleVenta", back_populates="producto")

    @property
    def ganancia_unitaria(self) -> float:
        return round(self.precio_venta - self.costo_compra, 2)

    @property
    def margen_porcentaje(self) -> float:
        if self.precio_venta <= 0:
            return 0.0
        return round(((self.precio_venta - self.costo_compra) / self.precio_venta) * 100, 1)

    @property
    def rentabilidad_sobre_costo(self) -> float:
        if self.costo_compra <= 0:
            return 0.0
        return round(((self.precio_venta - self.costo_compra) / self.costo_compra) * 100, 1)

    @property
    def valor_inventario_costo(self) -> float:
        return round(max(self.stock_actual, 0) * self.costo_compra, 2)

    @property
    def valor_inventario_venta(self) -> float:
        return round(max(self.stock_actual, 0) * self.precio_venta, 2)

    @property
    def utilidad_potencial_stock(self) -> float:
        return round(max(self.stock_actual, 0) * self.ganancia_unitaria, 2)

    @property
    def bajo_stock(self) -> bool:
        return self.stock_actual <= self.stock_minimo


class MovimientoInventario(Base):
    __tablename__ = "movimientos_inventario"

    id = Column(Integer, primary_key=True, index=True)
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=False, index=True)
    tipo = Column(String(40), nullable=False)  # ENTRADA_PROVEEDOR, AJUSTE_POSITIVO, AJUSTE_NEGATIVO, VENTA, ANULACION_VENTA
    cantidad = Column(Integer, nullable=False)
    stock_resultante = Column(Integer, nullable=False, default=0)
    costo_unitario = Column(Float, nullable=False, default=2700.0)
    costo_total = Column(Float, nullable=False, default=0.0)
    proveedor = Column(String(120), nullable=True, default="Proveedor Principal")
    metodo_pago = Column(String(40), nullable=True, default="EFECTIVO")
    monto_efectivo = Column(Float, nullable=False, default=0.0)
    monto_transferencia = Column(Float, nullable=False, default=0.0)
    observacion = Column(String(250), nullable=True, default="")
    fecha = Column(DateTime, default=datetime.now, nullable=False)

    producto = relationship("Producto", back_populates="movimientos")
