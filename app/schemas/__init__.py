from typing import List, Optional
from pydantic import BaseModel, Field, model_validator


class ClienteSchema(BaseModel):
    nombre: str = Field(..., min_length=2, max_length=150)
    documento: Optional[str] = ""
    telefono: Optional[str] = ""
    direccion: Optional[str] = ""
    tipo_cliente: str = "Frecuente"
    cupo_credito: float = Field(default=500000.0, ge=0)
    notas: Optional[str] = ""


class ProductoSchema(BaseModel):
    codigo: str = Field(..., min_length=1, max_length=50)
    nombre: str = Field(..., min_length=2, max_length=150)
    sabor: Optional[str] = "Tradicional"
    presentacion: str = "Paquete Unidad"
    costo_compra: float = Field(default=2700.0, ge=0)
    precio_venta: float = Field(default=4000.0, gt=0)
    stock_actual: int = Field(default=0, ge=0)
    stock_minimo: int = Field(default=20, ge=0)


class ItemVentaInput(BaseModel):
    producto_id: int
    cantidad: int = Field(..., gt=0)
    precio_unitario: Optional[float] = Field(default=None, gt=0)


class RegistrarVentaSchema(BaseModel):
    cliente_id: int
    items: List[ItemVentaInput]
    descuento: float = Field(default=0.0, ge=0)
    pagado_efectivo: float = Field(default=0.0, ge=0)
    pagado_transferencia: float = Field(default=0.0, ge=0)
    referencia_transferencia: Optional[str] = ""
    notas: Optional[str] = ""


class RegistrarAbonoSchema(BaseModel):
    venta_id: int
    monto_efectivo: float = Field(default=0.0, ge=0)
    monto_transferencia: float = Field(default=0.0, ge=0)
    entidad_transferencia: Optional[str] = "Nequi / Transferencia"
    concepto: Optional[str] = ""

    @model_validator(mode="after")
    def validar_monto_positivo(self):
        total = round(self.monto_efectivo + self.monto_transferencia, 2)
        if total <= 0:
            raise ValueError("El monto total del abono (Efectivo + Transferencia) debe ser mayor a $0.")
        return self
