r"""
Configuración del sistema de detección facial.

En vez de tener la cadena de conexión escrita directamente en cada
notebook/script (como estaba antes: "SERVER=ASUS1\\SQLEXPRESS"),
la sacamos aquí y la leemos de variables de entorno si existen.

Para usarla en tu equipo, lo más simple es exportar las variables
antes de correr el script, por ejemplo en Windows (cmd):

    set FACEID_DB_SERVER=ASUS1\SQLEXPRESS
    set FACEID_DB_DATABASE=EmpresaDeteccionFacial

O simplemente dejar los valores por defecto de abajo si no quieres
configurar nada todavía, y cambiarlos aquí directamente.
"""

import os

# ---- Base de datos ----
DB_SERVER = os.environ.get("FACEID_DB_SERVER", r"ASUS1\SQLEXPRESS")
DB_DATABASE = os.environ.get("FACEID_DB_DATABASE", "EmpresaDeteccionFacial")
DB_DRIVER = os.environ.get("FACEID_DB_DRIVER", "{SQL Server}")


def get_connection_string() -> str:
    return (
        f"DRIVER={DB_DRIVER};"
        f"SERVER={DB_SERVER};"
        f"DATABASE={DB_DATABASE};"
        f"Trusted_Connection=yes"
    )


# ---- Rostros ----
RUTA_ROSTROS = os.environ.get("FACEID_RUTA_ROSTROS", "rostros_conocidos")

# Cuántas fotos capturar por empleado al registrarlo.
# Más fotos = mejor precisión de reconocimiento (dentro de lo razonable).
FOTOS_POR_EMPLEADO = 15

# Umbral de distancia para considerar un rostro "reconocido".
# Con face_recognition, valores típicos van de 0.0 (idéntico) a ~1.0.
# 0.45-0.55 es razonablemente estricto. Si el sistema rechaza gente
# que sí está registrada, sube un poco (ej 0.55-0.6). Si confunde
# personas distintas, bájalo (ej 0.4).
UMBRAL_RECONOCIMIENTO = 0.5

# Segundos que deben pasar antes de volver a registrar un evento
# (entrada/salida) para la misma persona, para evitar duplicados
# si se queda parada frente a la cámara.
COOLDOWN_SEGUNDOS = 20
