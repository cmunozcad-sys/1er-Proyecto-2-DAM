import argparse
import sys
import time

import pandas as pd

import analiticas
import config
import pipeline
import visualizaciones
from utils.trazas import crear_logger, guardar_csv

MODOS = {
    "real": (config.ENTRADA_REAL, "REAL", "real"),
    "sintetico": (config.ENTRADA_SINTETICA, "SINTETICO", "sintetico"),
    "errores": (config.ENTRADA_SINTETICA_ERRORES, "SINTETICO", "sintetico_errores"),
}


def calcular_resultados(datos, carpeta_entrada):
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
        "12_reconciliacion_sql": analiticas.reconciliacion_sql(datos, carpeta_entrada),
        "kpis": analiticas.calcular_kpis(datos),
        "comparacion_periodo_anterior": analiticas.comparar_periodo_anterior(datos),
        "estadisticos": analiticas.estadisticos(datos),
        "hipotesis": analiticas.hipotesis(datos),
        "limitaciones": analiticas.limitaciones(datos),
        "demanda_modelo_mes": analiticas.demanda_modelo_mes(datos),
        "catalogo_variables": analiticas.catalogo_variables(),
    }


def ejecutar(carpeta_entrada, origen, carpeta_salida, figuras=True):
    logger = crear_logger("pipeline", config.LOGS / "pipeline.log")
    inicio = time.perf_counter()
    carpeta_csv = carpeta_salida / "csv"

    tablas, manifiesto, registro = pipeline.cargar_datos(carpeta_entrada, origen)
    validas, resumen = pipeline.validar_datos(tablas, registro)
    lineas, pedidos = pipeline.integrar_datos(validas, registro)
    incidencias = registro.a_dataframe()

    guardar_csv(manifiesto, carpeta_csv / "manifiesto.csv")
    guardar_csv(resumen, carpeta_csv / "resumen_calidad.csv")
    guardar_csv(incidencias, carpeta_csv / "incidencias.csv")
    guardar_csv(analiticas.calidad_datos(resumen, incidencias), carpeta_csv / "09_calidad_datos.csv")
    guardar_csv(analiticas.incidencias_por_regla(incidencias), carpeta_csv / "09_incidencias_por_regla.csv")

    print(resumen.to_string(index=False))
    print(f"\nIncidencias: {len(incidencias)}")

    if registro.hay_bloqueantes() or pedidos is None:
        logger.error(f"Ejecución bloqueada | origen={origen} | no se publican resultados")
        print("\nHay incidencias BLOQUEANTES: no se publican KPIs ni gráficos.")
        print(f"Revisa {carpeta_csv / 'incidencias.csv'}")
        return False

    datos = analiticas.aplicar_filtros(analiticas.preparar_datos(validas, lineas, pedidos, origen))
    resultados = calcular_resultados(datos, carpeta_entrada)

    indice = []
    for nombre, df in resultados.items():
        guardar_csv(df, carpeta_csv / f"{nombre}.csv")
        indice.append({"fichero": f"{nombre}.csv", "filas": len(df), "origen": origen, "fecha_corte": str(datos["fecha_corte"].date()), "funcion": df.attrs.get("funcion", nombre)})
    guardar_csv(pd.DataFrame(indice), carpeta_csv / "indice_resultados.csv")

    if figuras:
        visualizaciones.guardar_figuras(datos, carpeta_salida / "figuras")

    duracion = time.perf_counter() - inicio
    logger.info(f"Ejecución correcta | origen={origen} | resultados={len(resultados)} | duracion={duracion:.2f}s")

    print("\n" + resultados["kpis"][["kpi", "valor", "unidad"]].to_string(index=False))
    print(f"\nResultados guardados en {carpeta_salida} ({duracion:.1f} s)")
    return True


def leer_argumentos():
    argumentos = argparse.ArgumentParser(description="Análisis de datos de Sneaker Factory")
    argumentos.add_argument("--modo", choices=MODOS, default="real",  help="real: CSV de Acceso a Datos · sintetico: histórico simulado · " "errores: copia sintética con errores introducidos")
    argumentos.add_argument("--sin-figuras", action="store_true", help="no genera los PNG")
    return argumentos.parse_args()


if __name__ == "__main__":
    opciones = leer_argumentos()
    carpeta, origen, subcarpeta = MODOS[opciones.modo]
    print(f"Modo {opciones.modo.upper()} · datos {origen} · entrada {carpeta}\n")
    correcto = ejecutar(carpeta, origen, config.SALIDA / subcarpeta, figuras=not opciones.sin_figuras)
    sys.exit(0 if correcto else 1)