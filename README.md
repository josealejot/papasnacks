# papasnacks

Sistema de Gestión Comercial y Control de Capital para **Inversiones "El Profeta"**.

## Características
- **Control de Inventario**: Gestión de productos, snacks, stock mínimo y trazabilidad de movimientos.
- **Ventas y Facturación**: Registro de ventas a contado y crédito con generación de comprobantes en PDF.
- **Gestión de Cartera**: Control de cuentas por cobrar, cupos de crédito, abonos y estado de cuentas de clientes.
- **Control de Capital y Flujo de Caja**: Monitoreo de capital de trabajo, activos líquidos, cuentas por cobrar, inventario y gastos operativos.
- **Reportes**: Exportación de balances y transacciones en formatos Excel (.xlsx) y PDF.

## Tecnologías
- **Backend**: FastAPI, SQLAlchemy, Pydantic
- **Base de Datos**: SQLite / PostgreSQL
- **Frontend / Plantillas**: Jinja2, HTML5, CSS3, JavaScript
- **Servidor**: Uvicorn
- **Exportación**: ReportLab (PDF), OpenPyXL (Excel)

## Instalación y Ejecución

1. Clonar el repositorio:
   ```bash
   git clone https://github.com/josealejot/papasnacks.git
   cd papasnacks
   ```

2. Instalar dependencias:
   ```bash
   pip install -r requirements.txt
   ```

3. Variables de entorno:
   Copiar `.env.example` a `.env` si se requiere modificar configuraciones.

4. Iniciar la aplicación:
   ```bash
   python run.py
   ```
   Acceder desde el navegador a: `http://127.0.0.1:8000`
