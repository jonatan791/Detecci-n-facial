"""
Capa de acceso a la base de datos.

Toda la lógica de SQL vive aquí, separada de la cámara y del
reconocimiento facial. Trabaja siempre con IdEmpleado (no con
nombre en texto libre), enlazado a la tabla Empleados definida
en SQLDeteccionFacialIngreso_v2.sql.
"""

import pyodbc
from datetime import datetime
from config import get_connection_string


def conectar():
    """Abre la conexión a SQL Server. Lanza una excepción clara si falla."""
    try:
        return pyodbc.connect(get_connection_string())
    except pyodbc.Error as e:
        raise RuntimeError(
            "No se pudo conectar a la base de datos. Verifica que SQL Server "
            "esté encendido y que FACEID_DB_SERVER / FACEID_DB_DATABASE "
            f"(config.py) sean correctos. Detalle: {e}"
        )


def obtener_o_crear_empleado(cursor, conn, nombres: str, apellidos: str, carpeta: str) -> int:
    """
    Busca un empleado por su carpeta de rostros. Si no existe, lo crea.
    Devuelve el IdEmpleado.
    """
    cursor.execute("SELECT IdEmpleado FROM Empleados WHERE CarpetaRostros = ?", carpeta)
    row = cursor.fetchone()
    if row:
        return row.IdEmpleado

    cursor.execute(
        """
        INSERT INTO Empleados (Nombres, Apellidos, CarpetaRostros)
        OUTPUT INSERTED.IdEmpleado
        VALUES (?, ?, ?)
        """,
        nombres, apellidos, carpeta,
    )
    id_empleado = cursor.fetchone()[0]
    conn.commit()
    return id_empleado


def obtener_empleados_activos(cursor):
    """Lista todos los empleados activos, para cargar sus rostros conocidos."""
    cursor.execute(
        """
        SELECT IdEmpleado, Nombres, Apellidos, CarpetaRostros
        FROM Empleados
        WHERE Activo = 1
        """
    )
    return cursor.fetchall()


def obtener_estado_actual(cursor, id_empleado: int) -> str:
    """Devuelve 'esperando_entrada' o 'esperando_salida' según el último registro."""
    cursor.execute(
        """
        SELECT TOP 1 FechaHoraSalida
        FROM Asistencia
        WHERE IdEmpleado = ?
        ORDER BY FechaHoraIngreso DESC
        """,
        id_empleado,
    )
    row = cursor.fetchone()
    if row and row.FechaHoraSalida is None:
        return "esperando_salida"
    return "esperando_entrada"


def registrar_ingreso(cursor, conn, id_empleado: int) -> datetime:
    now = datetime.now()
    cursor.execute(
        "INSERT INTO Asistencia (IdEmpleado, FechaHoraIngreso) VALUES (?, ?)",
        id_empleado, now,
    )
    conn.commit()
    return now


def registrar_salida(cursor, conn, id_empleado: int) -> datetime:
    now = datetime.now()
    cursor.execute(
        """
        UPDATE Asistencia
        SET FechaHoraSalida = ?
        WHERE IdAsistencia = (
            SELECT TOP 1 IdAsistencia
            FROM Asistencia
            WHERE IdEmpleado = ? AND FechaHoraSalida IS NULL
            ORDER BY FechaHoraIngreso DESC
        )
        """,
        now, id_empleado,
    )
    conn.commit()
    return now


def obtener_ultimos_registros(cursor, id_empleado: int, top: int = 5):
    cursor.execute(
        """
        SELECT TOP (?) IdAsistencia, FechaHoraIngreso, FechaHoraSalida
        FROM Asistencia
        WHERE IdEmpleado = ?
        ORDER BY FechaHoraIngreso DESC
        """,
        top, id_empleado,
    )
    return cursor.fetchall()
