
import os
from functools import wraps

from flask import (
    Flask,
    jsonify,
    render_template,
    request,
    redirect,
    url_for,
    session
)

import mysql.connector
from werkzeug.security import check_password_hash


app = Flask(__name__)

# Clave para las sesiones de Flask.
# Configura PETRESCUE_SECRET_KEY en el entorno antes de producción.
app.secret_key = os.environ.get(
    "PETRESCUE_SECRET_KEY",
    "clave-local-petrescue-cambiar-antes-de-produccion"
)


# ==========================================
# 1. CONEXION A MYSQL
# ==========================================

def conectar_bd():
    return mysql.connector.connect(
        host="127.0.0.1",
        port=3307,
        user="root",
        password="",
        database="petrescue"
    )


# ==========================================
# 2. CONTROL DE ACCESO
# ==========================================

def admin_requerido(funcion):
    @wraps(funcion)
    def decorador(*args, **kwargs):

        if "id_usuario" not in session:
            return redirect(url_for("login"))

        if session.get("rol") != "ADMIN_ONG":
            session.clear()
            return "Acceso denegado", 403

        return funcion(*args, **kwargs)

    return decorador


# ==========================================
# 3. PAGINA PRINCIPAL
# ==========================================

@app.route("/")
def inicio():
    return render_template("index.html")


# ==========================================
# 4. INICIO DE SESION
# ==========================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "GET":
        return render_template("login.html", error=None)

    correo = request.form.get(
        "correo", ""
    ).strip().lower()

    contrasena = (
        request.form.get("password")
        or request.form.get("contrasena")
        or ""
    )

    if not correo or not contrasena:
        return render_template(
            "login.html",
            error="Ingresa tu correo y contraseña."
        ), 400

    conexion = None
    cursor = None

    try:
        conexion = conectar_bd()
        cursor = conexion.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                id_usuario,
                nombre,
                correo,
                password_hash,
                rol
            FROM usuarios
            WHERE correo = %s
        """, (correo,))

        usuario = cursor.fetchone()

        if (
            usuario
            and usuario["rol"] == "ADMIN_ONG"
            and check_password_hash(
                usuario["password_hash"],
                contrasena
            )
        ):
            session.clear()

            session["id_usuario"] = usuario["id_usuario"]
            session["nombre"] = usuario["nombre"]
            session["rol"] = usuario["rol"]

            return redirect(url_for("panel_admin"))

        return render_template(
            "login.html",
            error="Correo o contraseña incorrectos."
        ), 401

    except mysql.connector.Error:
        app.logger.exception(
            "Error durante el inicio de sesión"
        )

        return render_template(
            "login.html",
            error="No se pudo conectar con la base de datos."
        ), 500

    finally:
        if cursor:
            cursor.close()

        if conexion and conexion.is_connected():
            conexion.close()


# ==========================================
# 5. PANEL DE ADMINISTRACION
# ==========================================

@app.route("/admin")
@admin_requerido
def panel_admin():
    return render_template(
        "admin.html",
        nombre=session.get("nombre")
    )


# ==========================================
# 6. CERRAR SESION
# ==========================================

@app.route("/logout", methods=["POST"])
@admin_requerido
def logout():
    session.clear()
    return redirect(url_for("login"))


# ==========================================
# 7. API PUBLICA: ANIMALES DISPONIBLES
# ==========================================

@app.route("/api/animales", methods=["GET"])
def listar_animales():

    conexion = None
    cursor = None

    try:
        conexion = conectar_bd()
        cursor = conexion.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                id_animal,
                nombre,
                especie,
                edad,
                foto,
                descripcion,
                estado
            FROM animales
            WHERE estado = 'DISPONIBLE'
        """)

        animales = cursor.fetchall()

        return jsonify(animales)

    except mysql.connector.Error:
        app.logger.exception(
            "Error al consultar animales"
        )

        return jsonify({
            "error": "No se pudo consultar el catálogo"
        }), 500

    finally:
        if cursor:
            cursor.close()

        if conexion and conexion.is_connected():
            conexion.close()


# ==========================================
# 8. API PRIVADA: SOLICITUDES DE ADOPCION
# ==========================================

@app.route("/api/solicitudes", methods=["GET"])
@admin_requerido
def listar_solicitudes():

    conexion = None
    cursor = None

    try:
        conexion = conectar_bd()
        cursor = conexion.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                id_solicitud,
                id_animal,
                nombre_postulante,
                correo,
                telefono,
                direccion,
                identificacion,
                motivo,
                estado,
                fecha_solicitud
            FROM solicitudes_adopcion
            ORDER BY fecha_solicitud DESC
        """)

        solicitudes = cursor.fetchall()

        return jsonify(solicitudes)

    except mysql.connector.Error:
        app.logger.exception(
            "Error al consultar solicitudes"
        )

        return jsonify({
            "error": "No se pudieron consultar las solicitudes"
        }), 500

    finally:
        if cursor:
            cursor.close()

        if conexion and conexion.is_connected():
            conexion.close()


# ==========================================
# 9. FORMULARIO DE SOLICITUD DE ADOPCION
# ==========================================

@app.route("/solicitud", methods=["GET", "POST"])
def solicitud():

    conexion = None
    cursor = None

    try:
        if request.method == "POST":
            id_animal = request.form.get(
                "id_animal", ""
            )
        else:
            id_animal = request.args.get(
                "id_animal", ""
            )

        if not id_animal.isdigit():
            return "ID de animal no válido", 400

        conexion = conectar_bd()
        cursor = conexion.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                id_animal,
                nombre,
                especie,
                edad,
                estado
            FROM animales
            WHERE id_animal = %s
        """, (int(id_animal),))

        animal = cursor.fetchone()

        if not animal:
            return "Animal no encontrado", 404

        if animal["estado"] != "DISPONIBLE":
            return "Este animal ya no está disponible", 409

        if request.method == "GET":
            return render_template(
                "solicitud.html",
                animal=animal,
                mensaje=None
            )

        # Datos del postulante
        nombre = request.form.get(
            "nombre", ""
        ).strip()

        correo = request.form.get(
            "correo", ""
        ).strip().lower()

        telefono = request.form.get(
            "telefono", ""
        ).strip()

        direccion = request.form.get(
            "direccion", ""
        ).strip()

        identificacion = request.form.get(
            "identificacion", ""
        ).strip()

        motivo = request.form.get(
            "motivo", ""
        ).strip()

        if not all([
            nombre,
            correo,
            telefono,
            direccion,
            identificacion
        ]):
            return "Completa todos los campos obligatorios", 400

        cursor.execute("""
            INSERT INTO solicitudes_adopcion (
                id_animal,
                nombre_postulante,
                correo,
                telefono,
                direccion,
                identificacion,
                motivo
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            int(id_animal),
            nombre,
            correo,
            telefono,
            direccion,
            identificacion,
            motivo
        ))

        conexion.commit()

        return render_template(
            "solicitud.html",
            animal=animal,
            mensaje="¡Solicitud registrada correctamente!"
        )

    except mysql.connector.Error:
        if conexion and conexion.is_connected():
            conexion.rollback()

        app.logger.exception(
            "Error al procesar la solicitud"
        )

        return (
            "Ocurrió un error al procesar la solicitud. "
            "Revisa la terminal de Visual Studio Code.",
            500
        )

    finally:
        if cursor:
            cursor.close()

        if conexion and conexion.is_connected():
            conexion.close()


# ==========================================
# 10. INICIAR SERVIDOR
# ==========================================

if __name__ == "__main__":
    app.run(debug=True)