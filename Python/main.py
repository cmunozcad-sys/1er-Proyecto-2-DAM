import argparse
import sys
import time
from datetime import date

import pandas as pd

import analiticas
import config
import pipeline
import prediccion
import visualizaciones
from utils.trazas import con_linaje, crear_logger, guardar_csv
from pathlib import Path

MODOS = {
    "real": (config.ENTRADA_REAL, "REAL", "real"),
    "sintetico": (config.ENTRADA_SINTETICA, "SINTETICO", "sintetico"),
    "errores": (config.ENTRADA_SINTETICA_ERRORES, "SINTETICO", "sintetico_errores"),
}
FASES = ["calidad", "descriptivo", "segmentacion", "prediccion", "completo"]


def calcular_resultados(datos, completos, carpeta_entrada):
    return {
        "01_pedidos_unicos": analiticas.pedidos_unicos(datos),
        "02_ventas_por_periodo": analiticas.ventas_por_periodo(datos),
        "03_modelos_abc": analiticas.modelos_abc(datos),
        "04_matriz_modelo_talla": analiticas.matriz_modelo_talla(datos),
        "04_matriz_modelo_talla_pct": analiticas.matriz_modelo_talla(datos, proporcion=True),
        "05_custom_vs_estandar": analiticas.custom_vs_estandar(datos),
        "06_clientes_rfm": analiticas.clientes_rfm(datos),
        "07_cohortes": analiticas.cohortes(datos),
        "08_stock_cobertura": analiticas.stock_cobertura(datos),
        "10_anomalias": analiticas.anomalias(datos),
        "11_margen": analiticas.margen(datos),
        "12_reconciliacion_sql": analiticas.reconciliacion_sql(completos, carpeta_entrada),
        "kpis": analiticas.calcular_kpis(datos),
        "comparacion_periodo_anterior": analiticas.comparar_periodo_anterior(datos),
        "estadisticos": analiticas.estadisticos(datos),
        "hipotesis": analiticas.hipotesis(datos),
        "limitaciones": analiticas.limitaciones(datos),
        "demanda_modelo_mes": analiticas.demanda_modelo_mes(datos),
        "catalogo_variables": analiticas.con_metadatos(analiticas.catalogo_variables(), "catalogo_variables", datos, {}, 0, "catalogo_variables"),
    }


def tabla_estado(estado, nombre, datos, funcion):
    return analiticas.con_metadatos(pd.DataFrame({"estado": [estado]}), nombre, datos, datos.get("filtros", {}), 1, funcion)


def ejecutar(carpeta_entrada, origen, carpeta_salida, figuras=True, filtros=None, fase="completo"):
    logger = crear_logger("pipeline", config.LOGS / "pipeline.log")
    inicio = time.perf_counter()
    carpeta_csv = carpeta_salida / "csv"

    tablas, manifiesto, registro = pipeline.cargar_datos(carpeta_entrada, origen)
    validas, resumen = pipeline.validar_datos(tablas, registro)
    lineas, pedidos = pipeline.integrar_datos(validas, registro)
    incidencias = registro.a_dataframe()

    contexto = {"origen": origen, "fecha_corte": None, "ejecucion": pd.Timestamp.now()}
    filas_entrada = int(resumen["filas_entrada"].sum())
    calidad = {
        "manifiesto": (manifiesto, "cargar_datos"),
        "resumen_calidad": (resumen, "validar_datos"),
        "incidencias": (incidencias, "validar_datos"),
        "09_calidad_datos": (analiticas.calidad_datos(resumen, incidencias), "calidad_datos"),
        "09_incidencias_por_regla": (analiticas.incidencias_por_regla(incidencias), "incidencias_por_regla"),
    }
    for nombre, (df, funcion) in calidad.items():
        analiticas.con_metadatos(df, nombre, contexto, {}, filas_entrada, funcion)
        guardar_csv(con_linaje(df), carpeta_csv / f"{nombre}.csv")

    print(resumen.to_string(index=False))
    print(f"\nIncidencias: {len(incidencias)}")

    if registro.hay_bloqueantes() or pedidos is None:
        logger.error(f"Ejecución bloqueada | origen={origen} | no se publican resultados")
        print("\nHay incidencias BLOQUEANTES: no se publican KPIs ni gráficos.")
        print(f"Revisa {carpeta_csv / 'incidencias.csv'}")
        return False

    if fase == "calidad":
        duracion = time.perf_counter() - inicio
        logger.info(f"Ejecución correcta | origen={origen} | fase=calidad | resultados={len(calidad)} | duracion={duracion:.2f}s")
        print(f"\nFase calidad: resultados guardados en {carpeta_csv} ({duracion:.1f} s)")
        return True

    completos = analiticas.preparar_datos(validas, lineas, pedidos, origen, contexto["ejecucion"])
    datos = analiticas.aplicar_filtros(completos, filtros)
    if datos["pedidos"].empty:
        logger.warning(f"Ejecución sin resultados | origen={origen} | ningún pedido cumple los filtros")
        print("\nNingún pedido cumple los filtros elegidos: no se publican KPIs ni gráficos. Prueba a quitar alguno.")
        return False

    resultados = {}
    if fase in ("descriptivo", "completo"):
        resultados.update(calcular_resultados(datos, completos, carpeta_entrada))
        resultados["cohortes_estado"] = tabla_estado(resultados["07_cohortes"].attrs["estado"], "cohortes_estado", datos, "cohortes")

    if fase in ("segmentacion", "completo"):
        if "06_clientes_rfm" not in resultados:
            resultados["06_clientes_rfm"] = analiticas.clientes_rfm(datos)
        clusters = analiticas.clustering_clientes(datos)
        for nombre in ("evaluacion", "perfil", "asignacion", "comparacion_rfm"):
            resultados[f"clusters_{nombre}"] = clusters[nombre]
        resultados["clusters_estado"] = tabla_estado(clusters["estado"], "clusters_estado", datos, "clustering_clientes")

    predicho = None
    if fase in ("prediccion", "completo"):
        if "demanda_modelo_mes" not in resultados:
            resultados["demanda_modelo_mes"] = analiticas.demanda_modelo_mes(datos)
        predicho = prediccion.evaluar_prediccion(datos)
        for nombre in ("metricas", "por_modelo", "serie", "detalle"):
            resultados[f"prediccion_{nombre}"] = predicho[nombre]
        resultados["prediccion_estado"] = tabla_estado(predicho["estado"], "prediccion_estado", datos, "evaluar_prediccion")

    indice = []
    for nombre, df in resultados.items():
        guardar_csv(con_linaje(df), carpeta_csv / f"{nombre}.csv")
        indice.append({"fichero": f"{nombre}.csv", "filas": len(df), "origen": origen, "fecha_corte": str(datos["fecha_corte"].date()), "funcion": df.attrs.get("funcion", nombre)})
    guardar_csv(pd.DataFrame(indice), carpeta_csv / "indice_resultados.csv")

    if figuras and fase in ("descriptivo", "completo"):
        visualizaciones.guardar_figuras(datos, carpeta_salida / "figuras")
    if figuras and predicho is not None and not predicho["serie"].empty:
        (carpeta_salida / "figuras").mkdir(parents=True, exist_ok=True)
        figura = prediccion.figura_real_vs_prediccion(predicho, datos)
        figura.savefig(carpeta_salida / "figuras" / "09_real_frente_prediccion.png", bbox_inches="tight")

    duracion = time.perf_counter() - inicio
    logger.info(f"Ejecución correcta | origen={origen} | fase={fase} | resultados={len(resultados)} | duracion={duracion:.2f}s")

    if "kpis" in resultados:
        print("\n" + resultados["kpis"][["kpi", "valor", "unidad"]].to_string(index=False))
    for nombre in ("clusters_estado", "prediccion_estado"):
        if nombre in resultados and fase != "completo":
            print(f"\n{resultados[nombre]['estado'].iloc[0]}")
    prefijo = "Resultados" if fase == "completo" else f"Fase {fase}: resultados"
    print(f"\n{prefijo} guardados en {carpeta_salida} ({duracion:.1f} s)")
    return True


def fecha(texto):
    try:
        date.fromisoformat(texto)
    except ValueError:
        raise argparse.ArgumentTypeError(f"fecha no válida: '{texto}' (formato AAAA-MM-DD)")
    return texto


def leer_argumentos(argv=None):
    argumentos = argparse.ArgumentParser(description="Análisis de datos de Sneaker Factory")
    argumentos.add_argument("--modo", choices=MODOS, default="real",  help="real: CSV de Acceso a Datos · sintetico: histórico simulado · " "errores: copia sintética con errores introducidos")
    argumentos.add_argument("--fase", choices=FASES, default="completo", help="calidad: solo carga y validación · descriptivo: KPIs, análisis y gráficos · segmentacion: RFM y clustering · prediccion: predicción de demanda · completo: todo (por defecto)")
    argumentos.add_argument("--sin-figuras", action="store_true", help="no genera los PNG")
    argumentos.add_argument("--entrada", type=Path, help="carpeta con los CSV; por defecto la del modo")
    argumentos.add_argument("--salida", type=Path, help="carpeta de resultados; por defecto outputs/<modo>")
    argumentos.add_argument("--desde", type=fecha, help="fecha inicial AAAA-MM-DD")
    argumentos.add_argument("--hasta", type=fecha, help="fecha final AAAA-MM-DD")
    argumentos.add_argument("--modelo", nargs="+", default=[], help="id_modelo")
    argumentos.add_argument("--talla", type=float, nargs="+", default=[])
    argumentos.add_argument("--tipo", choices=config.TIPOS_PEDIDO, nargs="+", default=[])
    argumentos.add_argument("--estado", choices=config.ESTADOS_PEDIDO, nargs="+", default=[])
    argumentos.add_argument("--cliente", nargs="+", default=[], help="id_cliente")
    return argumentos.parse_args(argv)

def filtros_de(opciones):
    return {
        "fecha_desde": opciones.desde,
        "fecha_hasta": opciones.hasta,
        "modelos": opciones.modelo,
        "tallas": opciones.talla,
        "tipos": opciones.tipo,
        "estados": opciones.estado,
        "clientes": opciones.cliente,
    }


if __name__ == "__main__":
    opciones = leer_argumentos()
    carpeta, origen, subcarpeta = MODOS[opciones.modo]
    carpeta = opciones.entrada or carpeta
    salida = opciones.salida or config.SALIDA / subcarpeta
    filtros = filtros_de(opciones)
    fase = "" if opciones.fase == "completo" else f" · fase {opciones.fase}"
    print(f"Modo {opciones.modo.upper()}{fase} · datos {origen} · entrada {carpeta} · salida {salida}\n")
    correcto = ejecutar(carpeta, origen, salida, figuras=not opciones.sin_figuras, filtros=filtros, fase=opciones.fase)
    sys.exit(0 if correcto else 1)