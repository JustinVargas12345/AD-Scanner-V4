import os
from datetime import datetime

LOG_FILE = "ad_scanner.log"
LOG_MAX_LINES = 1000

def escribir_log(mensaje, tipo="INFO"):
    """
    Escribe un mensaje en el log con timestamp y tipo de mensaje.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    linea = f"[{timestamp}] [{tipo}] {mensaje}\n"
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(linea)






def eliminar_logs():
    """
    Revisa el archivo de logs y elimina las líneas más antiguas si supera LOG_MAX_LINES.
    Solo conserva las últimas LOG_MAX_LINES.
    """
    if not os.path.exists(LOG_FILE):
        return  # No hay archivo que limpiar

    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            lineas = f.readlines()

        if len(lineas) > LOG_MAX_LINES:
            # Solo conservar las últimas LOG_MAX_LINES
            lineas = lineas[-LOG_MAX_LINES:]
            with open(LOG_FILE, "w", encoding="utf-8") as f:
                f.writelines(lineas)
            print(f"[INFO] Logs limpiados automáticamente. Se conservaron las últimas {LOG_MAX_LINES} líneas.")
    except Exception as e:
        print(f"[ERROR] No se pudo limpiar el log: {e}")

    