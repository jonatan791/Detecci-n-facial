"""
Detección facial para registrar entrada/salida de empleados.

Cambios respecto a la versión anterior (detector_ingreso.ipynb):
  - Usa face_recognition (embeddings de 128D) en vez de Haar cascade
    + LBPHFaceRecognizer. Es mucho más preciso: en el notebook
    original, personas SÍ registradas daban confianzas de 90-113
    con un umbral de 70 (o sea, casi nunca se reconocían bien).
  - Los rostros conocidos se cargan a partir de la tabla Empleados
    (no listando carpetas a ciegas), así que cada rostro queda
    ligado a un IdEmpleado real desde el principio.
  - Los registros de entrada/salida se hacen con IdEmpleado, no con
    nombre en texto libre, evitando el problema de "Jonatan Carcamo"
    vs "Jonatan CarcamoS" que tenías antes.
  - Cooldown y umbral configurables desde config.py.

Requisitos (ver requirements.txt):
    pip install face_recognition opencv-python pyodbc numpy pandas openpyxl

Nota sobre seguridad: este sistema, igual que el original, NO tiene
detección de vida (liveness) — una foto en un celular podría engañarlo.
Si esto se usa para control de asistencia real, ese es el siguiente
paso recomendado después de este cambio.
"""

import os
import subprocess
import time

import cv2
import face_recognition
import numpy as np
import pandas as pd

import db
from config import RUTA_ROSTROS, UMBRAL_RECONOCIMIENTO, COOLDOWN_SEGUNDOS


def cargar_rostros_conocidos(cursor):
    """
    Recorre los empleados activos en la BD, y para cada uno calcula
    el encoding (embedding) de cada una de sus fotos guardadas.
    Devuelve tres listas paralelas: encodings, id_empleado, nombre_completo.
    """
    encodings = []
    ids_empleado = []
    nombres_completos = []

    empleados = db.obtener_empleados_activos(cursor)
    print(f"Cargando rostros de {len(empleados)} empleado(s)...")

    for emp in empleados:
        carpeta_path = os.path.join(RUTA_ROSTROS, emp.CarpetaRostros)
        if not os.path.isdir(carpeta_path):
            print(f"⚠️ No existe la carpeta '{carpeta_path}' para {emp.CarpetaRostros}, se omite.")
            continue

        nombre_completo = f"{emp.Nombres} {emp.Apellidos}"
        fotos_cargadas = 0

        for archivo in os.listdir(carpeta_path):
            ruta_foto = os.path.join(carpeta_path, archivo)
            imagen = face_recognition.load_image_file(ruta_foto)
            ubicaciones = face_recognition.face_locations(imagen, model="hog")
            if not ubicaciones:
                print(f"⚠️ No se detectó rostro en: {ruta_foto}")
                continue

            codificaciones = face_recognition.face_encodings(imagen, known_face_locations=ubicaciones)
            if not codificaciones:
                continue

            encodings.append(codificaciones[0])
            ids_empleado.append(emp.IdEmpleado)
            nombres_completos.append(nombre_completo)
            fotos_cargadas += 1

        if fotos_cargadas == 0:
            print(f"⚠️ {nombre_completo}: no se pudo cargar ninguna foto válida.")
        else:
            print(f"  {nombre_completo}: {fotos_cargadas} foto(s) cargadas")

    return encodings, ids_empleado, nombres_completos


def exportar_a_excel(cursor, id_empleado, nombre_completo):
    registros = db.obtener_ultimos_registros(cursor, id_empleado, top=5)
    datos = [
        {
            "ID": r.IdAsistencia,
            "Ingreso": r.FechaHoraIngreso.strftime("%Y-%m-%d %H:%M:%S") if r.FechaHoraIngreso else "",
            "Salida": r.FechaHoraSalida.strftime("%Y-%m-%d %H:%M:%S") if r.FechaHoraSalida else "",
        }
        for r in registros
    ]
    df = pd.DataFrame(datos)
    archivo = f"reporte_{nombre_completo.replace(' ', '_')}.xlsx"
    df.to_excel(archivo, index=False)
    print(f"✅ Exportado: {archivo}")
    try:
        os.startfile(archivo)  # más simple y confiable en Windows que subprocess+"start"
    except Exception:
        pass


def main():
    conn = db.conectar()
    cursor = conn.cursor()

    encodings_conocidos, ids_empleado, nombres_completos = cargar_rostros_conocidos(cursor)
    if not encodings_conocidos:
        print("❌ No hay rostros conocidos cargados. Registra empleados primero.")
        cursor.close()
        conn.close()
        return

    boton_coords = (10, 10, 220, 50)
    boton_presionado = False
    id_actual = None
    nombre_actual = ""
    registro_tiempos = {}  # id_empleado -> timestamp del último registro

    def click_event(event, x, y, flags, param):
        nonlocal boton_presionado
        x1, y1, x2, y2 = boton_coords
        if event == cv2.EVENT_LBUTTONDOWN and x1 <= x <= x2 and y1 <= y <= y2:
            boton_presionado = True

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        raise RuntimeError("No se pudo abrir la cámara.")

    cv2.namedWindow("Control de Asistencia")
    cv2.setMouseCallback("Control de Asistencia", click_event)

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            ubicaciones = face_recognition.face_locations(rgb, model="hog")
            codificaciones = face_recognition.face_encodings(rgb, known_face_locations=ubicaciones)

            for (top, right, bottom, left), encoding in zip(ubicaciones, codificaciones):
                distancias = face_recognition.face_distance(encodings_conocidos, encoding)
                mejor_idx = int(np.argmin(distancias)) if len(distancias) else None
                nombre_mostrado = "Desconocido"

                if mejor_idx is not None and distancias[mejor_idx] < UMBRAL_RECONOCIMIENTO:
                    id_empleado = ids_empleado[mejor_idx]
                    nombre_mostrado = nombres_completos[mejor_idx]

                    ahora = time.time()
                    ultimo = registro_tiempos.get(id_empleado, 0)
                    if (ahora - ultimo) > COOLDOWN_SEGUNDOS:
                        estado = db.obtener_estado_actual(cursor, id_empleado)
                        if estado == "esperando_entrada":
                            hora = db.registrar_ingreso(cursor, conn, id_empleado)
                            print(f"🟢 Ingreso: {nombre_mostrado} a las {hora.strftime('%H:%M:%S')}")
                        else:
                            hora = db.registrar_salida(cursor, conn, id_empleado)
                            print(f"🔴 Salida: {nombre_mostrado} a las {hora.strftime('%H:%M:%S')}")
                        registro_tiempos[id_empleado] = ahora

                    id_actual = id_empleado
                    nombre_actual = nombre_mostrado

                cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
                cv2.putText(
                    frame, nombre_mostrado, (left, top - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2,
                )

            # Botón exportar
            x1, y1, x2, y2 = boton_coords
            color = (0, 255, 0) if boton_presionado else (0, 128, 255)
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, -1)
            cv2.putText(frame, "EXPORTAR EXCEL", (x1 + 10, y1 + 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)

            if boton_presionado:
                if id_actual is not None:
                    exportar_a_excel(cursor, id_actual, nombre_actual)
                boton_presionado = False

            cv2.imshow("Control de Asistencia", frame)
            if cv2.waitKey(1) & 0xFF in (ord('q'), ord('Q')):
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()
        cursor.close()
        conn.close()


if __name__ == "__main__":
    main()
