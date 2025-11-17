
import pyodbc
import time
from cryptography.fernet import Fernet  # <-- nuevo
from Configs.logs_utils import escribir_log

KEY_FILE = "secret.key"

def _cargar_fernet():
    try:
        with open(KEY_FILE, "rb") as f:
            key = f.read()
        return Fernet(key)
    except Exception as e:
        escribir_log(f"No se pudo cargar '{KEY_FILE}': {e}", tipo="WARNING")
        return None

def _maybe_decrypt(value):
    if not value:
        return value
    f = _cargar_fernet()
    if not f:
        return value
    try:
        return f.decrypt(value.encode()).decode()
    except Exception:
        return value


# ------------------------
# Validar credenciales SQL
# ------------------------
def validar_sql(config):
    """
    Valida conexión a SQL Server y devuelve:
    (True, "") si todo está correcto
    (False, "mensaje de error") cuando algo está mal
    """

    try:
        driver = config.get("DB_DRIVER")
        server = config.get("DB_SERVER")
        db = config.get("DB_NAME")
        trusted = config.get("DB_TRUSTED", "yes").lower()

        if not driver:
            return (False, "DB_DRIVER vacío o inválido")

        if not server:
            return (False, "DB_SERVER vacío o inválido")

        if not db:
            return (False, "DB_NAME vacío o inválido")

        # Preparar credenciales desencriptadas
        user = _maybe_decrypt(config.get("DB_USER", "")) if config.get("DB_USER") else ""
        password = _maybe_decrypt(config.get("DB_PASSWORD", "")) if config.get("DB_PASSWORD") else ""

        # Construir string de conexión
        if trusted == "yes":
            conn_str = (
                f"DRIVER={driver};"
                f"SERVER={server};"
                f"DATABASE={db};"
                "Trusted_Connection=yes;"
            )
        else:
            if not user:
                return (False, "DB_USER vacío o inválido")

            if not password:
                return (False, "DB_PASSWORD vacío o inválido")

            conn_str = (
                f"DRIVER={driver};"
                f"SERVER={server};"
                f"DATABASE={db};"
                f"UID={user};"
                f"PWD={password};"
            )

        # Intentar conectar
        try:
            conn = pyodbc.connect(conn_str, timeout=4)
            conn.close()
            return (True, "")
        except pyodbc.InterfaceError:
            return (False, "DB_DRIVER inválido o no instalado")
        except pyodbc.OperationalError as e:
            mensaje = str(e)

            if "server was not found" in mensaje.lower():
                return (False, "DB_SERVER inaccesible o incorrecto")

            if "login failed" in mensaje.lower():
                return (False, "Credenciales SQL incorrectas (usuario o contraseña)")

            if "cannot open database" in mensaje.lower():
                return (False, "DB_NAME incorrecto o no existe en el servidor")

            return (False, f"Error SQL inesperado: {mensaje}")

        except Exception as e:
            return (False, f"Error al validar SQL: {e}")

    except Exception as e:
        escribir_log(f"Excepción en validar_sql: {e}", tipo="ERROR")
        return (False, "Error desconocido validando SQL")


# ------------------------
# Conexión a SQL Server con reconexión
# ------------------------
def conectar_sql(config):
    """
    Intenta conectarse a SQL Server indefinidamente hasta que tenga éxito.
    Recibe un diccionario 'config' con los datos de conexión.
    Devuelve la conexión activa.
    """
    while True:
        try:
            DB_DRIVER = config["DB_DRIVER"]
            DB_SERVER = config["DB_SERVER"]
            DB_NAME = config["DB_NAME"]
            DB_TRUSTED = config.get("DB_TRUSTED", "yes")
            # Intentar desencriptar si es necesario
            DB_USER = _maybe_decrypt(config.get("DB_USER", "")) if config.get("DB_USER") else ""
            DB_PASSWORD = _maybe_decrypt(config.get("DB_PASSWORD", "")) if config.get("DB_PASSWORD") else ""

            if DB_TRUSTED.lower() == "yes":
                conn_str = (
                    f"DRIVER={DB_DRIVER};"
                    f"SERVER={DB_SERVER};"
                    f"DATABASE={DB_NAME};"
                    "Trusted_Connection=yes;"
                )
            else:
                conn_str = (
                    f"DRIVER={DB_DRIVER};"
                    f"SERVER={DB_SERVER};"
                    f"DATABASE={DB_NAME};"
                    f"UID={DB_USER};"
                    f"PWD={DB_PASSWORD};"
                )

            conn = pyodbc.connect(conn_str, timeout=5)
            print("[OK] Conectado a SQL Server correctamente.")
            return conn

        except pyodbc.Error as e:
            print(f"[ERROR] No se pudo conectar a SQL Server: {e}")
            print("  Reintentando en 5 segundos...")
            time.sleep(5)


# ------------------------
# Ejecutar query SQL con reintentos
# ------------------------
def ejecutar_sql(conn, query, params=(), reintentos=3, espera=5, config=None):
    """
    Ejecuta un query SQL con reconexión automática en caso de fallo.
    Si falla, reconecta usando 'config' y reintenta.
    """
    for intento in range(1, reintentos + 1):
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return True

        except pyodbc.OperationalError as e:
            print(f"[ERROR] Fallo de conexión: {e}")
            if config:
                print(f"  Reconectando y reintentando ({intento}/{reintentos})...")
                conn = conectar_sql(config)
            time.sleep(espera)

        except pyodbc.Error as e:
            print(f"[ERROR] SQL Error: {e}")
            return False

    print("[FATAL] No se pudo ejecutar la consulta tras varios intentos.")
    return False
