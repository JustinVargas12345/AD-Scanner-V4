from db_conexion import ejecutar_sql

def crear_tabla(conn, config):
    """
    Crea la tabla EquiposAD si no existe, usando reconexión automática.
    """
    query = """
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='EquiposAD' AND xtype='U')
        CREATE TABLE EquiposAD (
            Nombre NVARCHAR(255) PRIMARY KEY,
            SO NVARCHAR(255),
            Descripcion NVARCHAR(255),
            IP NVARCHAR(50),
            NombreDNS NVARCHAR(255),
            VersionSO NVARCHAR(255),
            CreadoEl NVARCHAR(100),
            UltimoLogon NVARCHAR(100),
            Responsable NVARCHAR(255),
            Ubicacion NVARCHAR(255),
            EstadoCuenta NVARCHAR(50),
            PingStatus NVARCHAR(50),
            TiempoPing NVARCHAR(50),
            ActivoTiempo NVARCHAR(30) NULL,
            InactivoDesde DATETIME NULL,
            EstadoAD NVARCHAR(50) DEFAULT 'Dentro de AD',
            UltimaActualizacion DATETIME DEFAULT GETDATE()
        )
    """
    if ejecutar_sql(conn, query, config=config):
        print("[OK] Tabla 'EquiposAD' verificada o creada.")
    else:
        print("[ERROR] No se pudo crear/verificar la tabla.")
