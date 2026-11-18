# Utilidades compartidas: logs, registro de incidencias y linaje de los resultados

import logging
from datetime import datetime
from pathlib import Path

import pandas as pd

# Gravedad de una incidencia: BLOQUEANTE impide publicar, RECUPERABLE rechaza el registro y ADVERTENCIA solo avisa
BLOQUEANTE = "BLOQUEANTE"
RECUPERABLE = "RECUPERABLE"
ADVERTENCIA = "ADVERTENCIA"


# Crea un logger que escribe en un fichero con fecha, nivel y mensaje. Si ya existe, no duplica el manejador
def crear_logger(nombre, ruta_fichero):
    ruta_fichero = Path(ruta_fichero)
    ruta_fichero.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(nombre)
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        manejador = logging.FileHandler(ruta_fichero, encoding="utf-8")
        formato = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s", "%Y-%m-%d %H:%M:%S")
        manejador.setFormatter(formato)
        logger.addHandler(manejador)

    return logger


# Datos de un CSV leído para el manifiesto: filas, columnas, tamaño y fecha
def fila_manifiesto(tabla, ruta, df):
    ruta = Path(ruta)
    return {
        "tabla": tabla,
        "fichero": ruta.name,
        "fecha_analisis": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "filas": len(df),
        "columnas": len(df.columns),
        "tamano_bytes": ruta.stat().st_size,
    }


# Guarda todas las incidencias que salen al cargar y validar los datos
class RegistroIncidencias:

    # Empieza con la lista vacía
    def __init__(self):
        self.incidencias = []

    # Añade una incidencia con su tabla, registro, regla, gravedad, descripción y tratamiento
    def anadir(self, tabla, registro, regla, gravedad, descripcion, tratamiento):
        self.incidencias.append({
            "tabla": tabla,
            "registro": registro,
            "regla": regla,
            "gravedad": gravedad,
            "descripcion": descripcion,
            "tratamiento": tratamiento,
        })

    # True si alguna incidencia es bloqueante
    def hay_bloqueantes(self):
        return any(i["gravedad"] == BLOQUEANTE for i in self.incidencias)

    # Pasa las incidencias a un DataFrame para guardarlas o enseñarlas
    def a_dataframe(self):
        columnas = ["tabla", "registro", "regla", "gravedad", "descripcion", "tratamiento"]
        return pd.DataFrame(self.incidencias, columns=columnas)


# Añade al final las columnas de linaje: origen, fecha de corte, ejecución, filtros (texto del tipo 'modelos=1,2; tallas=41'), filas y función
def con_linaje(df):
    meta = df.attrs
    partes = []
    for nombre, valor in (meta.get("filtros") or {}).items():
        if isinstance(valor, (list, tuple)):
            valor = ",".join(str(v) for v in valor)
        partes.append(f"{nombre}={valor}")
    return df.assign(
        linaje_origen=meta.get("origen", "-"),
        linaje_fecha_corte=meta.get("fecha_corte", "-"),
        linaje_ejecucion=meta.get("ejecucion", "-"),
        linaje_filtros="; ".join(partes) if partes else "sin filtros",
        linaje_filas_origen=meta.get("filas_origen", "-"),
        linaje_funcion=meta.get("funcion", "-"),
    )


# Guarda un DataFrame en CSV y crea la carpeta si no existe
def guardar_csv(df, ruta):
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(ruta, index=False, encoding="utf-8")