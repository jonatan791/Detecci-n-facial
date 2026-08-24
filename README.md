# Detecci-n-facial
Sistema que detecta los rostros de los trabajadores de una empresa para poder marcar su entrada y salida de su sitio de trabajo

PASOS:

1) En la terminal (dentro de tu carpeta del proyecto) corre: python registrar_empleado.py Te va a pedir Nombres y Apellidos por consola, luego abre la cámara y toma 15 fotos automáticamente mientras mueves un poco la cabeza. Al terminar, crea el empleado en la tabla Empleados. Repítelo una vez por cada persona que quieras registrar.

2) Revisa que se haya creado la carpeta rostros_conocidos\Nombre Apellido con las 15 fotos dentro. También puedes verificar en SQL Server Management Studio con: SELECT * FROM Empleados; deberías ver la fila nueva con su IdEmpleado.

3) Corre: python detector_ingreso.py Va a imprimir en consola cuántos rostros cargó por cada empleado. Si dice '0 empleados cargados' o 'no se detectó rostro', regístrate primero con el paso 1.

4) Párate frente a la cámara. Debería dibujarte un recuadro verde con tu nombre y, en la consola, ver el mensaje 🟢 Ingreso registrado. Aléjate y vuelve a pararte pasado el cooldown (20 segundos por defecto) para probar que ahora registre 🔴 Salida en vez de ingreso otra vez.
