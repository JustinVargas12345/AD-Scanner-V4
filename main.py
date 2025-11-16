
import time
from db_conexion import conectar_sql
from db_table import crear_tabla
from ad_utils import obtener_equipos_ad, insertar_o_actualizar
import gui_config
from logs_utils import eliminar_logs
# ------------------------
# BUCLE PRINCIPAL
# ------------------------
def main(config):
    PING_INTERVAL = int(config["PING_INTERVAL"])
    
    # Conectar a SQL pasando config
    conn = conectar_sql(config)
    if not conn:
        print("[ERROR] No se pudo conectar a la base de datos.")
        return

    # Crear la tabla si no existe
    crear_tabla(conn, config)

    try:
        while True:
            if config.get("LOG_MODE", "Manual").lower() == "automatico":
                eliminar_logs()
            # Obtener equipos de AD usando config actual
            equipos = obtener_equipos_ad(config)
            if not equipos:
                print("[WARN] No se encontraron equipos en AD.")
                time.sleep(PING_INTERVAL)
                continue

            equipos_ad_actuales = [eq["nombre"] for eq in equipos]

            # Insertar o actualizar equipos en DB usando ping
            insertar_o_actualizar(conn, equipos, equipos_ad_actuales, ping_interval=PING_INTERVAL)
            
            print(f"[INFO] Actualización completada. Esperando {PING_INTERVAL} segundos...\n")
            time.sleep(PING_INTERVAL)

    except KeyboardInterrupt:
        print("\n[INFO] Script detenido manualmente.")

    except Exception as e:
        print("[ERROR] Ocurrió un error inesperado:", e)


# ------------------------
# INICIO DEL PROGRAMA
# ------------------------
if __name__ == "__main__":
    config = gui_config.abrir_gui_pro()  # Devuelve config válida o {}

    if not config:
        print("[INFO] Configuración inválida o cancelada. Saliendo.")
    else:
        print("[INFO] Configuración cargada correctamente. Iniciando scanner...")
        main(config)
