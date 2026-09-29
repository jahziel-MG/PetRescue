import mysql.connector
from werkzeug.security import generate_password_hash
from getpass import getpass


def crear_administrador():
    conexion = None
    cursor = None

    try:
        # Conexión a la base de datos PetRescue
        conexion = mysql.connector.connect(
            host="127.0.0.1",
            port=3307,
            user="root",
            password="",
            database="petrescue"
        )

        cursor = conexion.cursor()

        print("\n=== CREAR ADMINISTRADOR PETRESCUE ===")

        nombre = input("Nombre: ").strip()
        correo = input("Correo: ").strip().lower()
        contrasena = getpass("Contraseña: ")

        if not nombre or not correo or not contrasena:
            print("Todos los campos son obligatorios.")
            return

        # Encriptar la contraseña mediante un hash
        password_hash = generate_password_hash(contrasena)

        # Registrar administrador
        consulta = """
            INSERT INTO usuarios
                (nombre, correo, password_hash, rol)
            VALUES (%s, %s, %s, %s)
        """

        valores = (
            nombre,
            correo,
            password_hash,
            "ADMIN_ONG"
        )

        cursor.execute(consulta, valores)
        conexion.commit()

        print("\nAdministrador creado correctamente.")

    except mysql.connector.IntegrityError:
        print("\nEse correo ya está registrado.")

    except mysql.connector.Error as error:
        if conexion and conexion.is_connected():
            conexion.rollback()

        print("\nError de MySQL:", error)

    finally:
        if cursor:
            cursor.close()

        if conexion and conexion.is_connected():
            conexion.close()


if __name__ == "__main__":
    crear_administrador()