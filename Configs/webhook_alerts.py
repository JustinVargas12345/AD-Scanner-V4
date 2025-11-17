'''
import json
import requests
from datetime import datetime, timedelta
import jwt  # pip install PyJWT
from Datos.db_conexion_extras import ejecutar_sql_reintento, ejecutar_sql_fetch
from Datos.db_conexion import ejecutar_sql

WEBHOOK_CONFIG_PATH = "Configs/personal_info/webhook_config.json"

def cargar_webhook_config():
    """
    Devuelve dict con keys:
      { "webhook_url": str or None, "min_seconds_inactivo": int, "webhook_secret": str or None }
    """
    default = {"webhook_url": None, "min_seconds_inactivo": 60, "webhook_secret": None}
    try:
        with open(WEBHOOK_CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            url = data.get("webhook_url") or data.get("url") or None
            min_sec = data.get("min_seconds_inactivo", data.get("min_seconds", 60))
            secret = data.get("webhook_secret") or None
            try:
                min_sec = int(min_sec)
            except Exception:
                min_sec = 60
            return {"webhook_url": url, "min_seconds_inactivo": min_sec, "webhook_secret": secret}
    except FileNotFoundError:
        return default
    except Exception as e:
        print("[WEBHOOK_CFG] Error leyendo config:", e)
        return default

def generar_jwt(secret, expiracion_segundos=3600):
    """
    Genera un JWT simple con expiración.
    """
    payload = {
        "exp": datetime.utcnow() + timedelta(seconds=expiracion_segundos),
        "iat": datetime.utcnow()
    }
    token = jwt.encode(payload, secret, algorithm="HS256")
    # PyJWT >= 2.0 devuelve str, antes bytes
    if isinstance(token, bytes):
        token = token.decode("utf-8")
    return token

def enviar_alertas_inactividad(conn):
    cfg = cargar_webhook_config()
    webhook_url = cfg["webhook_url"]
    min_seconds = cfg["min_seconds_inactivo"]
    secret = cfg.get("webhook_secret")

    if not webhook_url:
        print("[ALERTAS] No hay URL configurada. Saltando ciclo.")
        return

    crear_tabla_alertas = """
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='AlertasEnviadas' AND xtype='U')
        CREATE TABLE AlertasEnviadas (
            Nombre NVARCHAR(255),
            Fecha DATE
        )
    """
    ejecutar_sql_reintento(conn, crear_tabla_alertas, ())

    query_inactivos = """
        SELECT Nombre, IP, InactivoDesde, Descripcion, Responsable, Ubicacion
        FROM EquiposAD
        WHERE InactivoDesde IS NOT NULL
    """
    inactivos = ejecutar_sql_fetch(conn, query_inactivos)

    if not inactivos:
        print("[ALERTAS] Ningún equipo está inactivo.")
        return

    ahora = datetime.now()
    hoy = ahora.date()

    for row in inactivos:
        nombre, ip, inactivo_desde, descripcion, responsable, ubicacion = row

        if not inactivo_desde:
            continue
        if isinstance(inactivo_desde, str):
            try:
                inactivo_desde = datetime.fromisoformat(inactivo_desde)
            except Exception:
                try:
                    inactivo_desde = datetime.strptime(inactivo_desde, "%Y-%m-%d %H:%M:%S")
                except Exception:
                    print(f"[ALERTAS] No pude parsear InactivoDesde para {nombre}: {inactivo_desde}")
                    continue

        diff = ahora - inactivo_desde
        segundos_inactivo = diff.total_seconds()
        if segundos_inactivo < min_seconds:
            print(f"[ALERTAS] {nombre} inactivo {int(segundos_inactivo)}s < {min_seconds}s → se salta")
            continue

        query_verificar = "SELECT 1 FROM AlertasEnviadas WHERE Nombre = ? AND Fecha = ?"
        ya = ejecutar_sql_fetch(conn, query_verificar, params=(nombre, hoy))
        if ya:
            continue

        payload = {
            "servidor": nombre,
            "ip": ip,
            "descripcion": descripcion,
            "responsable": responsable,
            "ubicacion": ubicacion,
            "inactivo_desde": inactivo_desde.isoformat(),
            "segundos_inactivo": int(segundos_inactivo)
        }

        headers = {}
        if secret:
            headers["Authorization"] = f"Bearer {generar_jwt(secret)}"

        try:
            resp = requests.post(webhook_url, json=payload, headers=headers, timeout=8)
            print(f"[ALERTA] Enviada → {nombre} → {resp.status_code}")
            query_insert = "INSERT INTO AlertasEnviadas (Nombre, Fecha) VALUES (?, ?)"
            ejecutar_sql_reintento(conn, query_insert, params=(nombre, hoy))
        except Exception as e:
            print(f"[ERROR ALERTA] No se pudo enviar a {nombre}: {e}")
            print("[ALERTAS] Se reintentará en el próximo ciclo.")
'''

import json
import requests
from datetime import datetime, timedelta
from Datos.db_conexion_extras import ejecutar_sql_reintento, ejecutar_sql_fetch
from Datos.db_conexion import ejecutar_sql  # para INSERT/DDL si tu ejecutar_sql funciona bien

WEBHOOK_CONFIG_PATH = "Configs/personal_info/webhook_config.json"

def cargar_webhook_config():
    """
    Devuelve dict con keys:
      { "webhook_url": str or None, "min_seconds_inactivo": int }
    """
    default = {"webhook_url": None, "min_seconds_inactivo": 60}
    try:
        with open(WEBHOOK_CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            url = data.get("webhook_url") or data.get("url") or None
            min_sec = data.get("min_seconds_inactivo", data.get("min_seconds", 60))
            try:
                min_sec = int(min_sec)
            except Exception:
                min_sec = 60
            return {"webhook_url": url, "min_seconds_inactivo": min_sec}
    except FileNotFoundError:
        return default
    except Exception as e:
        print("[WEBHOOK_CFG] Error leyendo config:", e)
        return default


def enviar_alertas_inactividad(conn):
    """
    Busca EquiposAD con InactivoDesde != NULL y envía alerta
    a la URL configurada si el equipo lleva más de min_seconds_inactivo.
    Envía máximo 1 alerta por servidor por día (tabla AlertasEnviadas).
    Además actualiza la columna UltimaWebhook al enviar la alerta.
    """
    cfg = cargar_webhook_config()
    webhook_url = cfg["webhook_url"]
    min_seconds = cfg["min_seconds_inactivo"]

    if not webhook_url:
        print("[ALERTAS] No hay URL configurada. Saltando ciclo.")
        return

    # Crear tabla de alertas enviadas (previene duplicados diarios)
    crear_tabla_alertas = """
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='AlertasEnviadas' AND xtype='U')
        CREATE TABLE AlertasEnviadas (
            Nombre NVARCHAR(255),
            Fecha DATE
        )
    """
    ejecutar_sql_reintento(conn, crear_tabla_alertas, ())

    # Obtener equipos con InactivoDesde no nulo
    query_inactivos = """
        SELECT Nombre, IP, InactivoDesde, Descripcion, Responsable, Ubicacion
        FROM EquiposAD
        WHERE InactivoDesde IS NOT NULL
    """
    inactivos = ejecutar_sql_fetch(conn, query_inactivos)

    if not inactivos:
        print("[ALERTAS] Ningún equipo está inactivo.")
        return

    ahora = datetime.now()
    hoy = ahora.date()

    for row in inactivos:
        nombre, ip, inactivo_desde, descripcion, responsable, ubicacion = row

        if not inactivo_desde:
            continue
        if isinstance(inactivo_desde, str):
            try:
                inactivo_desde = datetime.fromisoformat(inactivo_desde)
            except Exception:
                try:
                    inactivo_desde = datetime.strptime(inactivo_desde, "%Y-%m-%d %H:%M:%S")
                except Exception:
                    print(f"[ALERTAS] No pude parsear InactivoDesde para {nombre}: {inactivo_desde}")
                    continue

        diff = ahora - inactivo_desde
        segundos_inactivo = diff.total_seconds()

        if segundos_inactivo < min_seconds:
            print(f"[ALERTAS] {nombre} inactivo desde {inactivo_desde} ({int(segundos_inactivo)}s) - menor a {min_seconds}s, se salta")
            continue

        # Verificar si YA SE ENVIÓ una alerta HOY
        query_verificar = "SELECT 1 FROM AlertasEnviadas WHERE Nombre = ? AND Fecha = ?"
        ya = ejecutar_sql_fetch(conn, query_verificar, params=(nombre, hoy)) if 'params' in ejecutar_sql_fetch.__code__.co_varnames else ejecutar_sql_fetch(conn, query_verificar)
        try:
            if ya:
                continue
        except Exception:
            ya = ejecutar_sql_fetch(conn, query_verificar)
            if ya:
                continue

        # Construir payload
        payload = {
            "servidor": nombre,
            "ip": ip,
            "descripcion": descripcion,
            "responsable": responsable,
            "ubicacion": ubicacion,
            "inactivo_desde": inactivo_desde.isoformat(),
            "segundos_inactivo": int(segundos_inactivo)
        }

        # Enviar (no bloquear el programa si falla)
        try:
            resp = requests.post(webhook_url, json=payload, timeout=8)
            print(f"[ALERTA] Enviada → {nombre} → {resp.status_code}")

            # Registrar alerta enviada
            query_insert = "INSERT INTO AlertasEnviadas (Nombre, Fecha) VALUES (?, ?)"
            ejecutar_sql_reintento(conn, query_insert, params=(nombre, hoy))

            # -----------------------------
            # Actualizar UltimaWebhook
            # -----------------------------
            query_update = "UPDATE EquiposAD SET UltimoWebhook = GETDATE() WHERE Nombre = ?"
            ejecutar_sql_reintento(conn, query_update, params=(nombre,))

        except Exception as e:
            print(f"[ERROR ALERTA] No se pudo enviar a {nombre}: {e}")
            print("[ALERTAS] Se reintentará en el próximo ciclo (programa continúa).")
