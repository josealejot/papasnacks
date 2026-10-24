import os
import uvicorn
from app import app, inicializar_datos_semilla

if __name__ == "__main__":
    inicializar_datos_semilla()
    port = int(os.getenv("PORT", 8000))
    print("=" * 68)
    print('  INVERSIONES "EL PROFETA" - SISTEMA DE GESTIÓN Y CONTROL DE CAPITAL')
    print(f"  NIT: 1020233725 | Tel: 3024645363")
    print(f"  Servidor activo en: http://127.0.0.1:{port}")
    print("=" * 68)
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=True)
