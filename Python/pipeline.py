from pathlib import Path

import pandas as pd

import config
from utils.trazas import (BLOQUEANTE, RECUPERABLE, ADVERTENCIA, RegistroIncidencias, crear_logger,fila_manifiesto, guardar_csv)
VALORES_VERDADERO = {"true", "t", "1", "si", "sí"}
VALORES_FALSO = {"false", "f", "0", "no"}


def leer_tabla(tabla, carpeta, registro):
    ruta = Path(carpeta) / config.FICHEROS[tabla]

    if not ruta.exists():
        registro.anadir(tabla, "-", "01", BLOQUEANTE, f"No existe el fichero {ruta.name}", "Carga abortada")
        return None, ruta

    try:
        df = pd.read_csv(ruta, sep=config.SEPARADOR, encoding=config.CODIFICACION, dtype=str, keep_default_na=False, na_values=config.VALORES_NULOS)
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


def id_registro(df, tabla, indice):
    return "-".join(str(df.at[indice, c]) for c in config.CLAVES[tabla])


def marcar(tabla, df, mascara, regla, gravedad, descripcion, tratamiento, registro):
    mascara = mascara.fillna(False).astype(bool)
    for indice in df.index[mascara]:
        registro.anadir(tabla, id_registro(df, tabla, indice), regla, gravedad, descripcion, tratamiento)
    return mascara


def duplicados_clave(tabla, df, registro, regla="02"):
    claves = config.CLAVES[tabla]
    repetidos = df.duplicated(subset=claves, keep=False)
    if not repetidos.any():
        return repetidos

    identicos = df.duplicated(keep="first")
    marcar(tabla, df, identicos, regla, RECUPERABLE, "Fila repetida idéntica",
           "Se conserva una sola copia", registro)

    conflictivos = repetidos & ~df.duplicated(keep=False)
    marcar(tabla, df, conflictivos, regla, RECUPERABLE, "Clave repetida con datos distintos",
           "Se rechazan todas las copias", registro)

    return identicos | conflictivos


def validar_clientes(df, registro):
    rechazar = duplicados_clave("clientes", df, registro)
    rechazar |= marcar("clientes", df, df["id_cliente"].isna(), "09", RECUPERABLE,
                       "Cliente sin identificador", "Registro rechazado", registro)
    marcar("clientes", df, ~df["tipo"].isin(config.TIPOS_CLIENTE), "07", ADVERTENCIA,
           f"Tipo de cliente fuera de {config.TIPOS_CLIENTE}", "Se conserva", registro)
    marcar("clientes", df, df["fecha_alta"].isna(), "04", ADVERTENCIA,
           "Fecha de alta nula o imposible", "Se conserva", registro)
    return df[~rechazar]


def validar_modelos(df, registro):
    rechazar = duplicados_clave("modelos", df, registro)
    rechazar |= marcar("modelos", df, df["id_modelo"].isna(), "09", RECUPERABLE,
                       "Modelo sin identificador", "Registro rechazado", registro)
    rechazar |= marcar("modelos", df, df["precio_base"].isna() | (df["precio_base"] <= 0), "06", RECUPERABLE,
                       "Precio base nulo, no numérico o no positivo", "Registro rechazado", registro)
    marcar("modelos", df, ~df["categoria"].isin(config.CATEGORIAS_MODELO), "07", ADVERTENCIA,
           f"Categoría fuera de {config.CATEGORIAS_MODELO}", "Se conserva", registro)
    return df[~rechazar]


def talla_valida(serie):
    return serie.between(config.TALLA_MIN, config.TALLA_MAX) & ((serie * 2) % 1 == 0)


def existe_en(df, columnas, destino):
    cruce = df[columnas].merge(destino[columnas].drop_duplicates(), on=columnas, how="left", indicator=True)
    return pd.Series((cruce["_merge"] == "both").to_numpy(), index=df.index)


def comprobar_referencia(tabla, df, pendiente, columnas, destino_csv, destino_valido, fichero, registro):
    con_valor = df[columnas].notna().all(axis=1)
    en_csv = existe_en(df, columnas, destino_csv)
    en_validos = existe_en(df, columnas, destino_valido)
    referencia = " y ".join(columnas)

    no_existe = marcar(tabla, df, pendiente & con_valor & ~en_csv, "03", BLOQUEANTE,
                       f"{referencia} no existe en {fichero}", "Registro rechazado", registro)
    rechazada = marcar(tabla, df, pendiente & con_valor & en_csv & ~en_validos, "03", RECUPERABLE,
                       f"{referencia} fue rechazado en {fichero}", "Registro rechazado", registro)
    return no_existe | rechazada


def validar_stock(df, modelos_csv, modelos, registro):
    rechazar = duplicados_clave("stock", df, registro, regla="11")
    rechazar |= marcar("stock", df, ~talla_valida(df["talla"]), "08", RECUPERABLE,
                       f"Talla fuera de {config.TALLA_MIN}-{config.TALLA_MAX}", "Registro rechazado", registro)
    rechazar |= marcar("stock", df, df["cantidad"].isna() | (df["cantidad"] < 0), "11", RECUPERABLE,
                       "Stock nulo o negativo", "Registro rechazado", registro)
    rechazar |= marcar("stock", df, df["id_modelo"].isna(), "09", RECUPERABLE,
                       "Stock sin modelo", "Registro rechazado", registro)
    rechazar |= comprobar_referencia("stock", df, ~rechazar, ["id_modelo"], modelos_csv, modelos,
                                     "modelos.csv", registro)
    return df[~rechazar]


def validar_pedidos(df, clientes_csv, clientes, registro, ahora):
    rechazar = duplicados_clave("pedidos", df, registro)
    rechazar |= marcar("pedidos", df, df["fecha_pedido"].isna() | (df["fecha_pedido"] > ahora), "04", RECUPERABLE,
                       "Fecha de pedido nula, imposible o futura", "Registro rechazado", registro)
    rechazar |= marcar("pedidos", df, ~df["estado"].isin(config.ESTADOS_PEDIDO), "07", RECUPERABLE,
                       f"Estado fuera de {config.ESTADOS_PEDIDO}", "Registro rechazado", registro)
    rechazar |= marcar("pedidos", df, ~df["tipo"].isin(config.TIPOS_PEDIDO), "07", RECUPERABLE,
                       f"Tipo fuera de {config.TIPOS_PEDIDO}", "Registro rechazado", registro)
    rechazar |= marcar("pedidos", df, df["id_cliente"].isna(), "09", RECUPERABLE,
                       "Pedido sin cliente", "Registro rechazado", registro)
    rechazar |= comprobar_referencia("pedidos", df, ~rechazar, ["id_cliente"], clientes_csv, clientes,
                                     "clientes.csv", registro)

    marcar("pedidos", df, df["fecha_confirmacion"] < df["fecha_pedido"], "12", ADVERTENCIA,
           "Confirmación anterior a la fecha de pedido", "Se conserva", registro)
    marcar("pedidos", df, df["fecha_entrega_prevista"] < df["fecha_pedido"].dt.normalize(), "12", ADVERTENCIA,
           "Entrega prevista anterior al pedido", "Se conserva", registro)
    marcar("pedidos", df, (df["estado"] == "CANCELADO") & df["fecha_cancelacion"].isna(), "12", ADVERTENCIA,
           "Pedido cancelado sin fecha de cancelación", "Se conserva", registro)
    marcar("pedidos", df, (df["estado"] != "CANCELADO") & df["fecha_cancelacion"].notna(), "12", ADVERTENCIA,
           "Fecha de cancelación en un pedido no cancelado", "Se conserva", registro)
    marcar("pedidos", df, (df["estado"] == "CONFIRMADO") & df["fecha_confirmacion"].isna(), "12", ADVERTENCIA,
           "Pedido confirmado sin fecha de confirmación", "Se conserva", registro)
    return df[~rechazar]


def validar_lineas(df, tablas, validas, registro):
    rechazar = duplicados_clave("lineas", df, registro)
    rechazar |= marcar("lineas", df, df["cantidad"].isna() | (df["cantidad"] <= 0), "05", RECUPERABLE,
                       "Cantidad nula, cero o negativa", "Registro rechazado", registro)
    rechazar |= marcar("lineas", df, df["precio_unitario"].isna() | (df["precio_unitario"] < 0), "06", RECUPERABLE,
                       "Precio unitario nulo, no numérico o negativo", "Registro rechazado", registro)
    rechazar |= marcar("lineas", df, ~talla_valida(df["talla"]), "08", RECUPERABLE,
                       f"Talla fuera de {config.TALLA_MIN}-{config.TALLA_MAX}", "Registro rechazado", registro)
    rechazar |= marcar("lineas", df, df["id_pedido"].isna() | df["id_modelo"].isna(), "09", RECUPERABLE,
                       "Línea sin pedido o sin modelo", "Registro rechazado", registro)

    rechazar |= comprobar_referencia("lineas", df, ~rechazar, ["id_pedido"], tablas["pedidos"],
                                     validas["pedidos"], "pedidos.csv", registro)
    rechazar |= comprobar_referencia("lineas", df, ~rechazar, ["id_modelo"], tablas["modelos"],
                                     validas["modelos"], "modelos.csv", registro)
    rechazar |= comprobar_referencia("lineas", df, ~rechazar, ["id_variante", "talla"], tablas["stock"],
                                     validas["stock"], "stock.csv", registro)

    variantes = validas["stock"][["id_variante", "talla", "id_modelo"]]
    cruce = df.merge(variantes, on=["id_variante", "talla"], how="left", suffixes=("", "_stock"),
                     validate="many_to_one")
    cruce.index = df.index
    otro_modelo = cruce["id_modelo_stock"].notna() & (cruce["id_modelo"] != cruce["id_modelo_stock"])
    marcar("lineas", df, ~rechazar & otro_modelo, "12", ADVERTENCIA,
           "El modelo no coincide con el de la variante en stock", "Se conserva", registro)

    aceptadas = df[~rechazar]
    repetidas = aceptadas.duplicated(subset=["id_pedido", "id_variante", "talla"], keep=False)
    marcar("lineas", df, repetidas.reindex(df.index, fill_value=False), "10", ADVERTENCIA,
           "Varias líneas con el mismo pedido, variante y talla", "Se conservan", registro)
    return df[~rechazar]


def comprobar_totales(pedidos, lineas, registro):
    importe = (lineas["cantidad"] * lineas["precio_unitario"]).groupby(lineas["id_pedido"]).sum()
    calculado = pedidos["id_pedido"].map(importe).fillna(0).round(2)
    sin_lineas = ~pedidos["id_pedido"].isin(lineas["id_pedido"])
    distinto = ~sin_lineas & ((calculado - pedidos["total"]).abs() > 0.01)
    marcar("pedidos", pedidos, distinto, "12", ADVERTENCIA,
           "El total no coincide con la suma de sus líneas", "Se usa la suma de las líneas", registro)
    marcar("pedidos", pedidos, sin_lineas, "12", ADVERTENCIA,
           "Pedido sin líneas válidas", "Se conserva en actividad", registro)


def resumen_calidad(tablas, validas, registro):
    incidencias = registro.a_dataframe()
    filas = []
    for tabla in config.FICHEROS:
        entrada = len(tablas[tabla]) if tabla in tablas else 0
        salida = len(validas[tabla]) if tabla in validas else 0
        propias = incidencias[incidencias["tabla"] == tabla]
        filas.append({
            "tabla": tabla,
            "filas_entrada": entrada,
            "filas_validas": salida,
            "filas_rechazadas": entrada - salida,
            "porcentaje_calidad": round(salida / entrada * 100, 2) if entrada else 0.0,
            "incidencias": len(propias),
            "bloqueantes": int((propias["gravedad"] == BLOQUEANTE).sum()),
        })
    return pd.DataFrame(filas)


def validar_datos(tablas, registro):
    if len(tablas) < len(config.FICHEROS):
        return {}, resumen_calidad(tablas, {}, registro)

    ahora = pd.Timestamp.now()
    validas = {}
    validas["clientes"] = validar_clientes(tablas["clientes"], registro)
    validas["modelos"] = validar_modelos(tablas["modelos"], registro)
    validas["stock"] = validar_stock(tablas["stock"], tablas["modelos"], validas["modelos"], registro)
    validas["pedidos"] = validar_pedidos(tablas["pedidos"], tablas["clientes"], validas["clientes"], registro, ahora)
    validas["lineas"] = validar_lineas(tablas["lineas"], tablas, validas, registro)
    comprobar_totales(validas["pedidos"], validas["lineas"], registro)

    return validas, resumen_calidad(tablas, validas, registro)

if __name__ == "__main__":
    tablas, manifiesto, registro = cargar_datos(config.ENTRADA_REAL, "REAL")
    validas, resumen = validar_datos(tablas, registro)
    incidencias = registro.a_dataframe()

    print(resumen.to_string(index=False))
    print()
    print(f"Incidencias: {len(incidencias)} | Bloqueantes: {registro.hay_bloqueantes()}")
    if not incidencias.empty:
        print(incidencias.to_string(index=False))

    carpeta = config.SALIDA / "real" / "csv"
    guardar_csv(manifiesto, carpeta / "manifiesto.csv")
    guardar_csv(resumen, carpeta / "resumen_calidad.csv")
    guardar_csv(incidencias, carpeta / "incidencias.csv")