"""
Registro de empleados (nuevo rostro conocido).

Cambios respecto a la versión anterior (registrar_empleado.ipynb):
  - El nombre se pide por consola (input) ANTES de abrir la cámara,
    en vez de capturar teclas dentro de la ventana de OpenCV. Esto
    elimina los problemas con tildes/ñ y con nombres mal escritos.
  - Usa face_recognition (HOG) para detectar el rostro en vez del
    Haar cascade, que era menos preciso.
  - Al terminar, crea (o reutiliza) el registro del empleado en la
    tabla Empleados de SQL Server, enlazando la carpeta de fotos
    con su IdEmpleado.
  - Guarda automáticamente N fotos (config.FOTOS_POR_EMPLEADO)
    espaciadas en el tiempo, pidiéndole a la persona que mueva
    ligeramente la cabeza, en vez de depender de que alguien haga
    clic manualmente en un botón repetidas veces.

Requisitos (ver requirements.txt):
    pip install face_recognition opencv-python pyodbc
"""

import os
import time

import cv2
import face_recognition

import db
from config import RUTA_ROSTROS, FOTOS_POR_EMPLEADO


def pedir_datos_empleado():
    print("=== Registro de nuevo empleado ===")
    nombres = input("Nombres: ").strip()
    apellidos = input("Apellidos: ").strip()
    while not nombres or not apellidos:
        print("Nombres y apellidos no pueden estar vacíos.")
        nombres = input("Nombres: ").strip()
        apellidos = input("Apellidos: ").strip()
    return nombres, apellidos


def capturar_fotos(carpeta_path: str, cantidad: int):
    """
    Abre la cámara y guarda 'cantidad' fotos del rostro detectado,
    con una pequeña pausa entre cada una para que la persona pueda
    girar levemente la cabeza (mejora la variedad del dataset).
    """
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        raise RuntimeError("No se pudo abrir la cámara. Verifica que esté conectada y libre.")

    guardadas = 0
    ultimo_guardado = 0
    intervalo_segundos = 1.0  # tiempo mínimo entre fotos

    print(f"Mostrando cámara. Se guardarán {cantidad} fotos automáticamente.")
    print("Mueve ligeramente la cabeza (izquierda/derecha/arriba/abajo) durante la captura.")
    print("Presiona 'q' para cancelar en cualquier momento.")

    while guardadas < cantidad:
        ret, frame = cap.read()
        if not ret:
            print("No se pudo leer un frame de la cámara.")
            break

        # face_recognition trabaja en RGB, OpenCV entrega BGR
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        ubicaciones = face_recognition.face_locations(rgb, model="hog")

        for (top, right, bottom, left) in ubicaciones:
            cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)

        cv2.putText(
            frame, f"Fotos: {guardadas}/{cantidad}", (15, 30),
            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2,
        )
        cv2.imshow("Registrar Empleado", frame)

        ahora = time.time()
        if ubicaciones and (ahora - ultimo_guardado) >= intervalo_segundos:
            # Usamos solo el primer rostro detectado en el frame
            top, right, bottom, left = ubicaciones[0]
            rostro = frame[top:bottom, left:right]
            if rostro.size > 0:
                nombre_archivo = f"foto_{guardadas:02d}.jpg"
                cv2.imwrite(os.path.join(carpeta_path, nombre_archivo), rostro)
                guardadas += 1
                ultimo_guardado = ahora
                print(f"✅ Foto {guardadas}/{cantidad} guardada")

        if cv2.waitKey(1) & 0xFF == ord('q'):
            print("Captura cancelada por el usuario.")
            break

    cap.release()
    cv2.destroyAllWindows()
    return guardadas


def main():
    nombres, apellidos = pedir_datos_empleado()
    carpeta = f"{nombres} {apellidos}"
    carpeta_path = os.path.join(RUTA_ROSTROS, carpeta)
    os.makedirs(carpeta_path, exist_ok=True)

    guardadas = capturar_fotos(carpeta_path, FOTOS_POR_EMPLEADO)
    if guardadas == 0:
        print("⚠️ No se guardó ninguna foto. Registro cancelado (no se creará en la base de datos).")
        return

    conn = db.conectar()
    cursor = conn.cursor()
    try:
        id_empleado = db.obtener_o_crear_empleado(cursor, conn, nombres, apellidos, carpeta)
        print(f"✅ Empleado registrado en la base de datos con IdEmpleado = {id_empleado}")
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    main()
