# Ciclo de refresco del dashboard: lee los CSV, los valida, recalcula y decide el estado

import time
from datetime import datetime
from pathlib import Path

import pandas as pd

import analiticas
import config
import pipeline
from utils.trazas import BLOQUEANTE, crear_logger

# Estados posibles de un ciclo
CORRECTO = "correcto"
SIN_CAMBIOS = "sin cambios"
DATOS_INVALIDOS = "datos inválidos"
ERROR_CARGA = "error de carga"

# Texto de la barra de estado según el origen de los datos
PROCEDENCIA = {"REAL": "ACC · REAL", "SINTETICO": "SINTÉTICO · LABORATORIO"}


# Huella de la carpeta: nombre, fecha de modificación y tamaño de cada CSV. Sirve para saber si han cambiado
def huella(carpeta):
    return tuple((f.name, f.stat().st_mtime_ns, f.stat().st_size) for f in sorted(Path(carpeta).glob("*.csv")))


# Dice si ya ha pasado el intervalo de refresco desde la última comprobación
def toca_ciclo(ultima_comprobacion, ahora=None):
    if ultima_comprobacion is None:
        return True
    ahora = ahora or datetime.now()
    intervalo = pd.Timedelta(config.INTERVALO_REFRESCO).total_seconds()
    return (ahora - ultima_comprobacion).total_seconds() >= intervalo - config.MARGEN_REFRESCO


# Ejecuta un ciclo completo y devuelve un diccionario con el estado, los datos y las incidencias
def ejecutar_ciclo(carpeta, origen, huella_anterior=None):
    logger = crear_logger("refresco", config.LOG_REFRESCO)
    inicio = time.perf_counter()
    comprobado = datetime.now()
    ciclo = {
        "origen": origen,
        "procedencia": PROCEDENCIA.get(origen, origen),
        "comprobado": comprobado,
        "huella": (),
        "datos": None,
        "resumen": pd.DataFrame(),
        "incidencias": pd.DataFrame(columns=["tabla", "registro", "regla", "gravedad", "descripcion", "tratamiento"]),
        "manifiesto": pd.DataFrame(),
        "filas_validas": 0,
        "explicacion": "",
    }

    try:
        # Cargar, validar e integrar los CSV con el pipeline
        ciclo["huella"] = huella(carpeta)
        tablas, manifiesto, registro = pipeline.cargar_datos(carpeta, origen)
        validas, resumen = pipeline.validar_datos(tablas, registro)
        lineas, pedidos = pipeline.integrar_datos(validas, registro)
        ciclo.update(resumen=resumen, incidencias=registro.a_dataframe(), manifiesto=manifiesto,
                     filas_validas=int(resumen["filas_validas"].sum()))

        # Decidir el estado: falta un fichero, datos inválidos, correcto o sin cambios
        faltan = [f for f in config.FICHEROS.values() if not (Path(carpeta) / f).exists()]
        if faltan:
            ciclo.update(estado=ERROR_CARGA, explicacion=f"No existe {', '.join(faltan)}")
        elif registro.hay_bloqueantes() or pedidos is None:
            incidencias = ciclo["incidencias"]
            bloqueantes = incidencias[incidencias["gravedad"] == BLOQUEANTE]
            textos = (bloqueantes["tabla"] + ": " + bloqueantes["descripcion"]).drop_duplicates()
            ciclo.update(estado=DATOS_INVALIDOS, explicacion="; ".join(textos.head(3)))
        else:
            ciclo["datos"] = analiticas.preparar_datos(validas, lineas, pedidos, origen, comprobado)
            ciclo["estado"] = SIN_CAMBIOS if ciclo["huella"] == huella_anterior else CORRECTO
    # Cualquier fallo al leer se trata como error de carga
    except Exception as error:
        ciclo.update(datos=None, estado=ERROR_CARGA, explicacion=f"{type(error).__name__} al leer los CSV")

    # Escribir una línea en logs/refresco.log (WARNING si no hay datos válidos)
    ciclo["duracion"] = time.perf_counter() - inicio
    resumen = ciclo["resumen"]
    filas = "-" if resumen.empty else " ".join(f"{f['tabla']}={f['filas_validas']}/{f['filas_entrada']}" for _, f in resumen.iterrows())
    linea = (f"origen={origen} | filas {filas} | duracion={ciclo['duracion']:.2f}s | "
             f"estado={ciclo['estado']} | anomalia={ciclo['explicacion'] or '-'}")
    if ciclo["datos"] is None:
        logger.warning(linea)
    else:
        logger.info(linea)
    return ciclo


# Si el ciclo es válido se publica; si no, se sigue mostrando el último válido
def publicar(ciclo, valido_anterior):
    return ciclo if ciclo["datos"] is not None else valido_anterior
