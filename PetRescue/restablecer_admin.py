import mysql.connector
from werkzeug.security import generate_password_hash
from getpass import getpass

nuevo_nombre = input("Nombre del administrador: ").strip()
nuevo_correo = input("Nuevo correo: ").strip().lower()
nueva_password = getpass("Nueva contraseña: ")

if not nuevo_nombre or not nuevo_correo or not nueva_password:
    print("Error: todos los campos son obligatorios.")
    raise SystemExit

conexion = None
cursor = None

try:
    conexion = mysql.connector.connect(
        host="localhost",
        port=3307,
        user="root",
        password="",
        database="petrescue"
    )

    cursor = conexion.cursor(dictionary=True)

    # Buscar al administrador actual
    cursor.execute(
        "SELECT id_usuario FROM usuarios WHERE rol = %s LIMIT 1",
        ("ADMIN_ONG",)
    )
    administrador = cursor.fetchone()

    if not administrador:
        print("No se encontró ningún administrador.")
        raise SystemExit

    # Comprobar que el correo no pertenezca a otro usuario
    cursor.execute(
        "SELECT id_usuario FROM usuarios WHERE correo = %s",
        (nuevo_correo,)
    )
    usuario_correo = cursor.fetchone()

    if (
        usuario_correo
        and usuario_correo["id_usuario"]
        != administrador["id_usuario"]
    ):
        print("Ese correo ya pertenece a otro usuario.")

    else:
        password_hash = generate_password_hash(nueva_password)

        cursor.execute(
            """
            UPDATE usuarios
            SET nombre = %s,
                correo = %s,
                password_hash = %s
            WHERE id_usuario = %s
            """,
            (
                nuevo_nombre,
                nuevo_correo,
                password_hash,
                administrador["id_usuario"]
            )
        )

        conexion.commit()
        print("\n¡Administrador actualizado correctamente!")
        print("Correo:", nuevo_correo)

except mysql.connector.Error as error:
    print("Error de MySQL:", error)

finally:
    if cursor:
        cursor.close()

    if conexion and conexion.is_connected():
        conexion.close()