import logging
from datetime import datetime
from pathlib import Path

import pandas as pd

BLOQUEANTE = "BLOQUEANTE"
RECUPERABLE = "RECUPERABLE"
ADVERTENCIA = "ADVERTENCIA"


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


class RegistroIncidencias:

    def __init__(self):
        self.incidencias = []

    def anadir(self, tabla, registro, regla, gravedad, descripcion, tratamiento):
        self.incidencias.append({
            "tabla": tabla,
            "registro": registro,
            "regla": regla,
            "gravedad": gravedad,
            "descripcion": descripcion,
            "tratamiento": tratamiento,
        })

    def hay_bloqueantes(self):
        return any(i["gravedad"] == BLOQUEANTE for i in self.incidencias)

    def a_dataframe(self):
        columnas = ["tabla", "registro", "regla", "gravedad", "descripcion", "tratamiento"]
        return pd.DataFrame(self.incidencias, columns=columnas)


def texto_filtros(filtros):
    if not filtros:
        return "sin filtros"
    partes = []
    for nombre, valor in filtros.items():
        if isinstance(valor, (list, tuple)):
            valor = ",".join(str(v) for v in valor)
        partes.append(f"{nombre}={valor}")
    return "; ".join(partes)


def con_linaje(df):
    meta = df.attrs
    return df.assign(
        linaje_origen=meta.get("origen", "-"),
        linaje_fecha_corte=meta.get("fecha_corte", "-"),
        linaje_ejecucion=meta.get("ejecucion", "-"),
        linaje_filtros=texto_filtros(meta.get("filtros")),
        linaje_filas_origen=meta.get("filas_origen", "-"),
        linaje_funcion=meta.get("funcion", "-"),
    )


def guardar_csv(df, ruta):
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(ruta, index=False, encoding="utf-8")