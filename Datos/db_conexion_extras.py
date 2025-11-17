# ---------------------------------------
# Archivo: Datos/db_conexion_extras.py
# Funciones adicionales para consultas SQL
# ---------------------------------------

import time
import pyodbc
from Datos.db_conexion import conectar_sql  # usa tu conexión actual con encriptación

# -----------------------------------------------------
# Query con reintentos y sin comprometer el original
# -----------------------------------------------------
def ejecutar_sql_reintento(conn, query, params=(), intentos=3, espera=2, fetch=False):
    """
    Ejecuta un SQL con reintentos seguros.
    Compatible con tu arquitectura sin alterar db_conexion.py.
    """
    ultimo_error = None

    for i in range(1, intentos + 1):
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)

            if fetch:
                datos = cursor.fetchall()
                conn.commit()
                return datos

            conn.commit()
            return True

        except Exception as e:
            ultimo_error = e
            print(f"[SQL RETRY] Error intento {i}/{intentos}: {e}")
            time.sleep(espera)

    print(f"[SQL RETRY] Falló definitivamente: {ultimo_error}")
    return None


# -----------------------------------------------------
# Query con fetch garantizado (para SELECT)
# -----------------------------------------------------
def ejecutar_sql_fetch(conn, query, params=()):
    """
    Solo SELECT. Devuelve listas de filas o [] si falla.
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query, params)
        return cursor.fetchall()
    except Exception as e:
        print("[SQL FETCH ERROR]", e)
        return []
