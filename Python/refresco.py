import time
from datetime import datetime
from pathlib import Path

import pandas as pd

import analiticas
import config
import pipeline
from utils.trazas import BLOQUEANTE, crear_logger

CORRECTO = "correcto"
SIN_CAMBIOS = "sin cambios"
DATOS_INVALIDOS = "datos inválidos"
ERROR_CARGA = "error de carga"

PROCEDENCIA = {"REAL": "ACC · REAL", "SINTETICO": "SINTÉTICO · LABORATORIO"}


def huella(carpeta):
    return tuple((f.name, f.stat().st_mtime_ns, f.stat().st_size) for f in sorted(Path(carpeta).glob("*.csv")))


def toca_ciclo(ultima_comprobacion, ahora=None):
    if ultima_comprobacion is None:
        return True
    ahora = ahora or datetime.now()
    intervalo = pd.Timedelta(config.INTERVALO_REFRESCO).total_seconds()
    return (ahora - ultima_comprobacion).total_seconds() >= intervalo - config.MARGEN_REFRESCO


def explicar_bloqueantes(incidencias):
    bloqueantes = incidencias[incidencias["gravedad"] == BLOQUEANTE]
    textos = (bloqueantes["tabla"] + ": " + bloqueantes["descripcion"]).drop_duplicates()
    return "; ".join(textos.head(3))


def texto_filas(resumen):
    if resumen.empty:
        return "-"
    return " ".join(f"{f['tabla']}={f['filas_validas']}/{f['filas_entrada']}" for _, f in resumen.iterrows())


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
        ciclo["huella"] = huella(carpeta)
        tablas, manifiesto, registro = pipeline.cargar_datos(carpeta, origen)
        validas, resumen = pipeline.validar_datos(tablas, registro)
        lineas, pedidos = pipeline.integrar_datos(validas, registro)
        ciclo.update(resumen=resumen, incidencias=registro.a_dataframe(), manifiesto=manifiesto,
                     filas_validas=int(resumen["filas_validas"].sum()))

        faltan = [f for f in config.FICHEROS.values() if not (Path(carpeta) / f).exists()]
        if faltan:
            ciclo.update(estado=ERROR_CARGA, explicacion=f"No existe {', '.join(faltan)}")
        elif registro.hay_bloqueantes() or pedidos is None:
            ciclo.update(estado=DATOS_INVALIDOS, explicacion=explicar_bloqueantes(ciclo["incidencias"]))
        else:
            ciclo["datos"] = analiticas.preparar_datos(validas, lineas, pedidos, origen, comprobado)
            ciclo["estado"] = SIN_CAMBIOS if ciclo["huella"] == huella_anterior else CORRECTO
    except Exception as error:
        ciclo.update(datos=None, estado=ERROR_CARGA, explicacion=f"{type(error).__name__} al leer los CSV")

    ciclo["duracion"] = time.perf_counter() - inicio
    linea = (f"origen={origen} | filas {texto_filas(ciclo['resumen'])} | duracion={ciclo['duracion']:.2f}s | "
             f"estado={ciclo['estado']} | anomalia={ciclo['explicacion'] or '-'}")
    if ciclo["datos"] is None:
        logger.warning(linea)
    else:
        logger.info(linea)
    return ciclo


def publicar(ciclo, valido_anterior):
    return ciclo if ciclo["datos"] is not None else valido_anterior
