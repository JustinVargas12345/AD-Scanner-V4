
import json
import os
import customtkinter as ctk
from tkinter import messagebox
from Modulos.ad_utils import validar_ad
from Configs.logs_utils import eliminar_logs
from Datos.db_conexion import conectar_sql   # <-- Validación SQL agregada
from cryptography.fernet import Fernet


CONFIG_FILE = "Config.json"
KEY_FILE = "secret.key"


# ---------------------------------------------------
# ENCRIPTACIÓN / DESENCRIPTACIÓN
# ---------------------------------------------------
def cargar_key():
    """Carga o genera la clave de encriptación."""
    if not os.path.exists(KEY_FILE):
        key = Fernet.generate_key()
        with open(KEY_FILE, "wb") as f:
            f.write(key)
    else:
        with open(KEY_FILE, "rb") as f:
            key = f.read()
    return Fernet(key)


fernet = cargar_key()


def encrypt_value(value):
    return fernet.encrypt(value.encode()).decode()


def decrypt_value(value):
    try:
        return fernet.decrypt(value.encode()).decode()
    except:
        return value


# ---------------------------------------------------
# CARGAR / GUARDAR CONFIG
# ---------------------------------------------------
def cargar_config():
    if not os.path.exists(CONFIG_FILE):
        return {}

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        for campo in ["AD_USER", "AD_PASSWORD", "DB_USER", "DB_PASSWORD"]:
            if campo in data and data[campo]:
                data[campo] = decrypt_value(data[campo])

        return data

    except:
        return {}


def guardar_config(values):
    try:
        int(values.get("PING_INTERVAL", ""))
    except ValueError:
        messagebox.showerror("Error", "PING_INTERVAL debe ser un número entero.")
        return False

    try:
        for campo in ["AD_USER", "AD_PASSWORD", "DB_USER", "DB_PASSWORD"]:
            if campo in values and values[campo]:
                values[campo] = encrypt_value(values[campo])

        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(values, f, indent=2)

        return True

    except Exception as e:
        messagebox.showerror("Error", f"No se pudo guardar la configuración:\n{e}")
        return False


# ---------------------------------------------------
# GUI PRINCIPAL
# ---------------------------------------------------
def abrir_gui_pro():
    config = cargar_config()

    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    root = ctk.CTk()
    root.title("Configuración AD Scanner – Pro")
    root.geometry("700x880")   # <-- Más grande (recomendación C)
    root.resizable(False, False)

    error_labels = {}

    # ---------------------------------------------------
    # FUNCIÓN PARA CREAR CAMPOS VISUALES
    # ---------------------------------------------------
    def campo(label, default, row, show=None):
        ctk.CTkLabel(root, text=label, font=("Segoe UI", 15)).grid(
            row=row, column=0, padx=25, pady=7, sticky="e"
        )

        entry = ctk.CTkEntry(root, width=430, show=show)  # <-- Más ancho
        entry.grid(row=row, column=1, pady=7, sticky="w")

        valor = config.get(label, default)
        entry.insert(0, "" if valor is None else valor)

        error = ctk.CTkLabel(root, text="", text_color="red", font=("Segoe UI", 12))
        error.grid(row=row+1, column=1, sticky="w")
        error_labels[label] = error

        return entry

    # --------------------------- CAMPOS AD ---------------------------
    ping = campo("PING_INTERVAL", "25", 0)
    ad_server = campo("AD_SERVER", "DC.lab.local", 2)
    ad_user = campo("AD_USER", "admin@lab.local", 4)
    ad_pass = campo("AD_PASSWORD", "TuClave", 6, show="*")
    ad_base = campo("AD_SEARCH_BASE", "DC=lab,DC=local", 8)

    def toggle_pass():
        ad_pass.configure(show="" if ad_pass.cget("show") == "*" else "*")
        btn_toggle.configure(text="O" if ad_pass.cget("show") == "" else "M")

    btn_toggle = ctk.CTkButton(root, text="M", width=40, command=toggle_pass)
    btn_toggle.grid(row=6, column=2, padx=5, sticky="w")

    # --------------------------- CAMPOS DB ---------------------------
    driver_options = [
        "ODBC Driver 17 for SQL Server",
        "ODBC Driver 18 for SQL Server",
        "ODBC Driver 13 for SQL Server"
    ]

    ctk.CTkLabel(root, text="DB_DRIVER", font=("Segoe UI", 15)).grid(
        row=10, column=0, padx=25, pady=7, sticky="e"
    )
    db_driver = ctk.CTkOptionMenu(root, values=driver_options, width=430)
    db_driver.grid(row=10, column=1, sticky="w")
    db_driver.set(config.get("DB_DRIVER", driver_options[0]))

    db_server = campo("DB_SERVER", ".\\SQLEXPRESS", 12)
    db_name = campo("DB_NAME", "DbAlgoritmo", 14)
    db_trusted = campo("DB_TRUSTED", "yes", 16)
    db_user = campo("DB_USER", "sa", 18)
    db_pass = campo("DB_PASSWORD", "Clave123", 20, show="*")

    def toggle_db_pass():
        db_pass.configure(show="" if db_pass.cget("show") == "*" else "*")
        btn_toggle_db.configure(text="O" if db_pass.cget("show") == "" else "M")

    btn_toggle_db = ctk.CTkButton(root, text="M", width=40, command=toggle_db_pass)
    btn_toggle_db.grid(row=20, column=2, padx=5, sticky="w")

    # --------------------------- LIMPIEZA LOGS ---------------------------
    ctk.CTkLabel(root, text="Modo Limpieza Logs", font=("Segoe UI", 15)).grid(
        row=22, column=0, padx=25, pady=7, sticky="e"
    )

    log_option_menu = ctk.CTkOptionMenu(
        root, values=["Manual", "Automático"], width=430
    )
    log_option_menu.grid(row=22, column=1, sticky="w")
    log_option_menu.set(config.get("LOG_MODE", "Manual"))

    config_result = {}

    # ---------------------------------------------------
    # BOTÓN GUARDAR
    # ---------------------------------------------------
    def click_guardar():
        nonlocal config_result

        for lbl in error_labels.values():
            lbl.configure(text="")

        errores = False

        # Validar ping
        try:
            int(ping.get())
        except ValueError:
            error_labels["PING_INTERVAL"].configure(text="Debe ser un número entero")
            errores = True

        # Validar AD
        credenciales_ad = {
            "AD_SERVER": ad_server.get(),
            "AD_USER": ad_user.get(),
            "AD_PASSWORD": ad_pass.get(),
            "AD_SEARCH_BASE": ad_base.get()
        }

        resultado = validar_ad(credenciales_ad)

        if not resultado["ok"]:
            campo_err = resultado["error"]

            if campo_err in error_labels:
                error_labels[campo_err].configure(text="Valor incorrecto")
            else:
                error_labels["AD_PASSWORD"].configure(text="Credenciales inválidas")

            errores = True

        if errores:
            return

        # Validar SQL SIN cerrar el GUI
        sql_config = {
            "DB_DRIVER": db_driver.get(),
            "DB_SERVER": db_server.get(),
            "DB_NAME": db_name.get(),
            "DB_TRUSTED": db_trusted.get(),
            "DB_USER": db_user.get(),
            "DB_PASSWORD": db_pass.get(),
        }

        try:
            conn = conectar_sql(sql_config)
            conn.close()

        except Exception:
            error_labels["DB_SERVER"].configure(text="No se pudo conectar a SQL Server")
            return

        # Preparar valores a guardar
        values = {
            "PING_INTERVAL": ping.get(),
            "AD_SERVER": ad_server.get(),
            "AD_USER": ad_user.get(),
            "AD_PASSWORD": ad_pass.get(),
            "AD_SEARCH_BASE": ad_base.get(),
            "DB_DRIVER": db_driver.get(),
            "DB_SERVER": db_server.get(),
            "DB_NAME": db_name.get(),
            "DB_TRUSTED": db_trusted.get(),
            "DB_USER": db_user.get() if db_trusted.get().lower() != "yes" else "",
            "DB_PASSWORD": db_pass.get() if db_trusted.get().lower() != "yes" else "",
            "LOG_MODE": log_option_menu.get()
        }

        # Guardar config
        if guardar_config(values):
            if values["LOG_MODE"].lower() == "automatico":
                eliminar_logs()

            config_result = values
            root.destroy()

    btn = ctk.CTkButton(
        root,
        text="Guardar Configuración",
        width=400,
        height=50,
        corner_radius=12,
        font=("Segoe UI", 16),
        command=click_guardar
    )
    btn.grid(row=24, column=0, columnspan=3, pady=45)

    root.mainloop()
    return config_result
