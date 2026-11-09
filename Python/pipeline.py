from pathlib import Path

import pandas as pd

import config
from utils.trazas import (BLOQUEANTE, ADVERTENCIA, RegistroIncidencias, crear_logger, fila_manifiesto, guardar_csv)

VALORES_VERDADERO = {"true", "t", "1", "si", "sí"}
VALORES_FALSO = {"false", "f", "0", "no"}


def leer_tabla(tabla, carpeta, registro):
    ruta = Path(carpeta) / config.FICHEROS[tabla]

    if not ruta.exists():
        registro.anadir(tabla, "-", "01", BLOQUEANTE, f"No existe el fichero {ruta.name}", "Carga abortada")
        return None, ruta

    try:
        df = pd.read_csv(ruta, sep=config.SEPARADOR, encoding=config.CODIFICACION, dtype=str,
                         keep_default_na=False, na_values=config.VALORES_NULOS)
    except pd.errors.EmptyDataError:
        registro.anadir(tabla, "-", "01", BLOQUEANTE, "Fichero vacío", "Carga abortada")
        return None, ruta

    df.columns = df.columns.str.strip()
    faltan = [c for c in config.COLUMNAS_OBLIGATORIAS[tabla] if c not in df.columns]

    if faltan:
        registro.anadir(tabla, "-", "01", BLOQUEANTE, f"Faltan columnas: {', '.join(faltan)}", "Carga abortada")
        return None, ruta

    if df.empty:
        registro.anadir(tabla, "-", "01", BLOQUEANTE, "Fichero sin filas de datos", "Carga abortada")
        return None, ruta

    return df, ruta


def anotar_fallos(tabla, df, columna, original, convertido, registro):
    fallos = original.notna() & convertido.isna()
    for indice in df.index[fallos]:
        registro.anadir(tabla, df.at[indice, config.CLAVES[tabla][0]], "CONV", ADVERTENCIA,
                        f"{columna}: no se pudo convertir '{original[indice]}'", "Valor tratado como nulo")


def convertir_booleano(serie):
    texto = serie.str.strip().str.lower()
    resultado = pd.Series(pd.NA, index=serie.index, dtype="boolean")
    resultado[texto.isin(VALORES_VERDADERO)] = True
    resultado[texto.isin(VALORES_FALSO)] = False
    return resultado


def convertir_tipos(tabla, df, registro):
    df = df.copy()

    for columna in df.columns:
        if df[columna].dtype == object or pd.api.types.is_string_dtype(df[columna]):
            df[columna] = df[columna].str.strip()

    for columna in config.COLUMNAS_NUMERICAS[tabla]:
        convertido = pd.to_numeric(df[columna], errors="coerce")
        anotar_fallos(tabla, df, columna, df[columna], convertido, registro)
        df[columna] = convertido

    for columna in config.COLUMNAS_FECHA[tabla]:
        convertido = pd.to_datetime(df[columna], errors="coerce", format="ISO8601")
        anotar_fallos(tabla, df, columna, df[columna], convertido, registro)
        df[columna] = convertido

    for columna in config.COLUMNAS_BOOLEANAS[tabla]:
        convertido = convertir_booleano(df[columna])
        anotar_fallos(tabla, df, columna, df[columna], convertido, registro)
        df[columna] = convertido

    return df


def cargar_datos(carpeta, origen):
    logger = crear_logger("pipeline", config.LOGS / "pipeline.log")
    registro = RegistroIncidencias()
    tablas = {}
    manifiesto = []

    logger.info(f"Inicio de carga | origen={origen} | carpeta={carpeta}")

    for tabla in config.FICHEROS:
        df, ruta = leer_tabla(tabla, carpeta, registro)
        if df is None:
            logger.error(f"{tabla}: carga abortada")
            continue

        fila = fila_manifiesto(tabla, ruta, df)
        fila["origen"] = origen
        manifiesto.append(fila)

        tablas[tabla] = convertir_tipos(tabla, df, registro)
        logger.info(f"{tabla}: {len(df)} filas leídas")

    logger.info(f"Fin de carga | incidencias={len(registro.incidencias)}")
    return tablas, pd.DataFrame(manifiesto), registro


if __name__ == "__main__":
    tablas, manifiesto, registro = cargar_datos(config.ENTRADA_REAL, "REAL")

    print(manifiesto.to_string(index=False))
    print()
    print(f"Incidencias: {len(registro.incidencias)}")
    if registro.incidencias:
        print(registro.a_dataframe().to_string(index=False))

    guardar_csv(manifiesto, config.SALIDA / "real" / "csv" / "manifiesto.csv")