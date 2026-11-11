from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

ENTRADA_REAL = BASE_DIR / "entrada"
ENTRADA_SINTETICA = BASE_DIR / "datos_sinteticos" / "normal"
ENTRADA_SINTETICA_ERRORES = BASE_DIR / "datos_sinteticos" / "con_errores"
SALIDA = BASE_DIR / "outputs"
LOGS = BASE_DIR / "logs"

SEPARADOR = ","
CODIFICACION = "utf-8"
VALORES_NULOS = ["NULL", ""]
MONEDA = "EUR"

FICHEROS = {
    "clientes": "clientes.csv",
    "modelos": "modelos.csv",
    "pedidos": "pedidos.csv",
    "lineas": "lineas_pedido.csv",
    "stock": "stock.csv",
}

COLUMNAS_OBLIGATORIAS = {
    "clientes": ["id_cliente", "ref_odoo", "tipo", "ciudad", "activo", "fecha_alta"],
    "modelos": ["id_modelo", "ref_odoo", "nombre", "categoria", "precio_base", "personalizable", "activo"],
    "pedidos": ["id_pedido", "ref_odoo", "tipo", "estado", "fecha_pedido", "fecha_entrega_prevista",
                "fecha_confirmacion", "fecha_cancelacion", "total", "id_cliente"],
    "lineas": ["id_linea", "id_pedido", "id_variante", "id_modelo", "color", "talla", "cantidad", "precio_unitario", "logo_club", "personalizada"],
    "stock": ["id_variante", "id_modelo", "color", "talla", "cantidad", "stock_minimo", "ultima_actualizacion"],
}

CLAVES = {
    "clientes": ["id_cliente"],
    "modelos": ["id_modelo"],
    "pedidos": ["id_pedido"],
    "lineas": ["id_linea"],
    "stock": ["id_variante", "talla"],
}

COLUMNAS_ID = ["id_cliente", "id_modelo", "id_pedido", "id_linea", "id_variante"]

COLUMNAS_FECHA = {
    "clientes": ["fecha_alta"],
    "modelos": [],
    "pedidos": ["fecha_pedido", "fecha_entrega_prevista", "fecha_confirmacion", "fecha_cancelacion"],
    "lineas": [],
    "stock": ["ultima_actualizacion"],
}

COLUMNAS_BOOLEANAS = {
    "clientes": ["activo"],
    "modelos": ["personalizable", "activo"],
    "pedidos": [],
    "lineas": ["logo_club", "personalizada"],
    "stock": [],
}

COLUMNAS_NUMERICAS = {
    "clientes": [],
    "modelos": ["precio_base"],
    "pedidos": ["total"],
    "lineas": ["talla", "cantidad", "precio_unitario"],
    "stock": ["talla", "cantidad", "stock_minimo"],
}

ESTADOS_PEDIDO = ["BORRADOR", "CONFIRMADO", "CANCELADO"]
ESTADOS_VENTA = ["CONFIRMADO"]
TIPOS_PEDIDO = ["ESTANDAR", "CUSTOM"]
TIPOS_CLIENTE = ["CLUB", "EQUIPO", "EMPRESA", "PARTICULAR"]
CATEGORIAS_MODELO = ["correr", "botas", "futbol", "baloncesto"]

TALLA_MIN = 30
TALLA_MAX = 48

DIAS_DEMANDA_RECIENTE = 28
UMBRAL_ABC_A = 0.80
UMBRAL_ABC_B = 0.95

DIAS_COBERTURA_RIESGO = 14
FACTOR_IQR = 1.5

FICHERO_REFERENCIA_SQL = "referencia_sql.csv"
MES_CONCILIACION = "2026-10"
TALLA_CONCILIACION = 42

SEMILLA = 42
MESES_PRUEBA = 3
MESES_MINIMOS_PREDICCION = 12
VALORES_K = [2, 3, 4, 5]

INTERVALO_REFRESCO = "60s"