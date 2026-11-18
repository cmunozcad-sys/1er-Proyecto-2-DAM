# Configuración común del análisis: rutas, contrato de datos, reglas de negocio y parámetros

from pathlib import Path

# Carpeta Python/ y carpetas de entrada, salida y logs
BASE_DIR = Path(__file__).resolve().parent

ENTRADA_REAL = BASE_DIR / "entrada"
ENTRADA_SINTETICA = BASE_DIR / "datos_sinteticos" / "normal"
ENTRADA_SINTETICA_ERRORES = BASE_DIR / "datos_sinteticos" / "con_errores"
SALIDA = BASE_DIR / "outputs"
LOGS = BASE_DIR / "logs"

# Formato de los CSV
SEPARADOR = ","
CODIFICACION = "utf-8"
VALORES_NULOS = ["NULL", ""]
MONEDA = "EUR"

# Nombre del CSV de cada tabla
FICHEROS = {
    "clientes": "clientes.csv",
    "modelos": "modelos.csv",
    "pedidos": "pedidos.csv",
    "lineas": "lineas_pedido.csv",
    "stock": "stock.csv",
}

# Columnas que tiene que traer cada CSV; si falta alguna, la carga se aborta
COLUMNAS_OBLIGATORIAS = {
    "clientes": ["id_cliente", "ref_odoo", "tipo", "ciudad", "activo", "fecha_alta"],
    "modelos": ["id_modelo", "ref_odoo", "nombre", "categoria", "precio_base", "personalizable", "activo"],
    "pedidos": ["id_pedido", "ref_odoo", "tipo", "estado", "fecha_pedido", "fecha_entrega_prevista",
                "fecha_confirmacion", "fecha_cancelacion", "total", "id_cliente"],
    "lineas": ["id_linea", "id_pedido", "id_variante", "id_modelo", "color", "talla", "cantidad", "precio_unitario", "logo_club", "personalizada"],
    "stock": ["id_variante", "id_modelo", "color", "talla", "cantidad", "stock_minimo", "ultima_actualizacion"],
}

# Clave primaria de cada tabla (en stock es variante + talla)
CLAVES = {
    "clientes": ["id_cliente"],
    "modelos": ["id_modelo"],
    "pedidos": ["id_pedido"],
    "lineas": ["id_linea"],
    "stock": ["id_variante", "talla"],
}

# Columnas que son identificadores
COLUMNAS_ID = ["id_cliente", "id_modelo", "id_pedido", "id_linea", "id_variante"]

# Columnas que se convierten a fecha
COLUMNAS_FECHA = {
    "clientes": ["fecha_alta"],
    "modelos": [],
    "pedidos": ["fecha_pedido", "fecha_entrega_prevista", "fecha_confirmacion", "fecha_cancelacion"],
    "lineas": [],
    "stock": ["ultima_actualizacion"],
}

# Columnas que se convierten a verdadero o falso
COLUMNAS_BOOLEANAS = {
    "clientes": ["activo"],
    "modelos": ["personalizable", "activo"],
    "pedidos": [],
    "lineas": ["logo_club", "personalizada"],
    "stock": [],
}

# Columnas que se convierten a número
COLUMNAS_NUMERICAS = {
    "clientes": [],
    "modelos": ["precio_base"],
    "pedidos": ["total"],
    "lineas": ["talla", "cantidad", "precio_unitario"],
    "stock": ["talla", "cantidad", "stock_minimo"],
}

# Valores permitidos. Solo los pedidos CONFIRMADO cuentan como venta
ESTADOS_PEDIDO = ["BORRADOR", "CONFIRMADO", "CANCELADO"]
ESTADOS_VENTA = ["CONFIRMADO"]
TIPOS_PEDIDO = ["ESTANDAR", "CUSTOM"]
TIPOS_CLIENTE = ["CLUB", "EQUIPO", "EMPRESA", "PARTICULAR"]
CATEGORIAS_MODELO = ["correr", "botas", "futbol", "baloncesto"]

# Rango de tallas válido
TALLA_MIN = 30
TALLA_MAX = 48

# Días de demanda reciente para la cobertura de stock y umbrales de la clasificación ABC
DIAS_DEMANDA_RECIENTE = 28
UMBRAL_ABC_A = 0.80
UMBRAL_ABC_B = 0.95

# Cobertura mínima antes de avisar de rotura y factor para detectar atípicos con IQR
DIAS_COBERTURA_RIESGO = 14
FACTOR_IQR = 1.5

# Casos mínimos por grupo y repeticiones del bootstrap en los contrastes de hipótesis
MUESTRA_MINIMA = 10
REPETICIONES_BOOTSTRAP = 2000

# Conciliación con SQL: fichero de referencia y el mes y la talla que se comparan
FICHERO_REFERENCIA_SQL = "referencia_sql.csv"
MES_CONCILIACION = "2026-10"
TALLA_CONCILIACION = 42

# Semilla para que todo sea reproducible y parámetros de la predicción y del clustering
SEMILLA = 42
MESES_PRUEBA = 3
MESES_MINIMOS_PREDICCION = 12
VALORES_K = [2, 3, 4, 5]

# Mínimos para poder calcular el clustering y las cohortes
MINIMO_CLIENTES_CLUSTER = 20
MINIMO_CLIENTES_COHORTES = 10
MESES_MINIMOS_COHORTES = 3

# Estacionalidad y cambios en la mezcla de tallas
MESES_MINIMOS_ESTACIONALIDAD = 12
UMBRAL_ESTACIONALIDAD = 1.3
MESES_MEZCLA_TALLAS = 6
UMBRAL_CAMBIO_TALLA = 2.0

# Refresco automático del dashboard
INTERVALO_REFRESCO = "60s"
MARGEN_REFRESCO = 5
LOG_REFRESCO = LOGS / "refresco.log"