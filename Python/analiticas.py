import numpy as np
import pandas as pd

import config
from pipeline import resumir_por_pedido

FILTROS_VACIOS = {
    "fecha_desde": None,
    "fecha_hasta": None,
    "modelos": [],
    "tallas": [],
    "tipos": [],
    "estados": [],
    "clientes": [],
}


def dividir(numerador, denominador):
    return numerador / denominador if denominador else np.nan


def con_metadatos(df, nombre, datos, filtros, filas_origen, funcion):
    df.attrs = {
        "nombre": nombre,
        "origen": datos["origen"],
        "fecha_corte": str(datos["fecha_corte"].date()),
        "filtros": {k: v for k, v in filtros.items() if v not in (None, [])},
        "filas_origen": int(filas_origen),
        "funcion": funcion,
        "reglas": f"Venta válida: estado en {config.ESTADOS_VENTA}",
    }
    return df


def preparar_datos(validas, lineas_enriquecidas, pedidos_unicos, origen):
    fecha_corte = pedidos_unicos["fecha_pedido"].max().normalize() + pd.Timedelta(days=1)
    return {
        "origen": origen,
        "fecha_corte": fecha_corte,
        "lineas": anadir_calendario(lineas_enriquecidas, fecha_corte),
        "pedidos": anadir_variables_pedido(anadir_calendario(pedidos_unicos, fecha_corte)),
        "clientes": validas["clientes"],
        "modelos": validas["modelos"],
        "stock": validas["stock"],
    }


def aplicar_filtros(datos, filtros=None):
    filtros = {**FILTROS_VACIOS, **(filtros or {})}
    pedidos = datos["pedidos"]
    lineas = datos["lineas"]

    mascara = pd.Series(True, index=pedidos.index)
    if filtros["fecha_desde"] is not None:
        mascara &= pedidos["fecha_pedido"] >= pd.Timestamp(filtros["fecha_desde"])
    if filtros["fecha_hasta"] is not None:
        mascara &= pedidos["fecha_pedido"] < pd.Timestamp(filtros["fecha_hasta"]) + pd.Timedelta(days=1)
    if filtros["tipos"]:
        mascara &= pedidos["tipo_pedido"].isin(filtros["tipos"])
    if filtros["estados"]:
        mascara &= pedidos["estado"].isin(filtros["estados"])
    if filtros["clientes"]:
        mascara &= pedidos["id_cliente"].isin(filtros["clientes"])
    pedidos = pedidos[mascara]

    lineas = lineas[lineas["id_pedido"].isin(pedidos["id_pedido"])]
    if filtros["modelos"]:
        lineas = lineas[lineas["id_modelo"].isin(filtros["modelos"])]
    if filtros["tallas"]:
        lineas = lineas[lineas["talla"].isin(filtros["tallas"])]

    if filtros["modelos"] or filtros["tallas"]:
        totales = resumir_por_pedido(lineas)
        pedidos = pedidos.drop(columns=["pares", "importe", "num_lineas", "num_modelos"])
        pedidos = pedidos.merge(totales, on="id_pedido", how="inner", validate="one_to_one")
        pedidos = anadir_variables_pedido(pedidos)

    return {**datos, "pedidos": pedidos, "lineas": lineas, "filtros": filtros}


def anadir_calendario(df, fecha_corte):
    df = df.copy()
    fecha = df["fecha_pedido"]
    df["anio"] = fecha.dt.year
    df["mes"] = fecha.dt.month
    df["trimestre"] = fecha.dt.quarter
    df["dia_semana"] = fecha.dt.day_of_week
    df["periodo"] = fecha.dt.to_period("M").astype(str)
    df["antiguedad_dias"] = (fecha_corte - fecha).dt.days
    return df


def anadir_variables_pedido(pedidos):
    pedidos = pedidos.copy()
    pedidos["ticket_pedido"] = pedidos["importe"]
    pedidos["precio_medio_par"] = (pedidos["importe"] / pedidos["pares"].replace(0, np.nan)).round(2)
    return pedidos


def ventas(datos):
    return datos["pedidos"][datos["pedidos"]["es_venta"]], datos["lineas"][datos["lineas"]["es_venta"]]


def variables_cliente(datos):
    pedidos, _ = ventas(datos)
    pedidos = pedidos.sort_values(["id_cliente", "fecha_pedido"])
    intervalo = pedidos.groupby("id_cliente")["fecha_pedido"].diff().dt.days

    df = pedidos.assign(intervalo=intervalo, es_custom=pedidos["tipo_pedido"] == "CUSTOM").groupby(
        "id_cliente").agg(
        frecuencia_cliente=("id_pedido", "nunique"),
        porcentaje_custom=("es_custom", "mean"),
        intervalo_medio_dias=("intervalo", "mean"),
    ).reset_index()
    df["porcentaje_custom"] = (df["porcentaje_custom"] * 100).round(2)
    df["intervalo_medio_dias"] = df["intervalo_medio_dias"].round(1)
    return df


def demanda_modelo_mes(datos):
    _, lineas = ventas(datos)
    meses = pd.period_range(datos["lineas"]["fecha_pedido"].min(), datos["fecha_corte"] - pd.Timedelta(days=1),
                            freq="M")
    modelos = datos["modelos"]["id_modelo"]
    rejilla = pd.MultiIndex.from_product([modelos, meses], names=["id_modelo", "mes"])

    unidades = lineas.groupby(["id_modelo", lineas["fecha_pedido"].dt.to_period("M").rename("mes")])["cantidad"].sum()
    df = unidades.reindex(rejilla, fill_value=0).rename("unidades_modelo_mes").reset_index()

    por_modelo = df.groupby("id_modelo")["unidades_modelo_mes"]
    df["demanda_mes_anterior"] = por_modelo.shift(1)
    df["media_3_meses_previos"] = por_modelo.transform(lambda s: s.shift(1).rolling(3).mean()).round(2)
    df["mes_del_anio"] = df["mes"].dt.month
    df["mes"] = df["mes"].astype(str)
    return df


def talla_mas_solicitada(datos):
    _, lineas = ventas(datos)
    por_talla = lineas.groupby(["id_modelo", "talla"])["cantidad"].sum().reset_index()
    maximo = por_talla.sort_values(["id_modelo", "cantidad", "talla"], ascending=[True, False, True])
    return maximo.drop_duplicates("id_modelo").rename(
        columns={"talla": "talla_mas_solicitada", "cantidad": "pares_talla"})


def catalogo_variables():
    filas = [
        ("anio", "Calendario", "año", "línea y pedido", "Fecha del pedido"),
        ("mes", "Calendario", "mes (1-12)", "línea y pedido", "Fecha del pedido"),
        ("trimestre", "Calendario", "trimestre (1-4)", "línea y pedido", "Fecha del pedido"),
        ("dia_semana", "Calendario", "0 = lunes", "línea y pedido", "Fecha del pedido"),
        ("antiguedad_dias", "Calendario", "días", "línea y pedido", "Fecha de corte"),
        ("importe_linea", "Economía", "EUR", "línea", "Al registrar la línea"),
        ("ticket_pedido", "Economía", "EUR", "pedido", "Al cerrar el pedido"),
        ("precio_medio_par", "Economía", "EUR/par", "pedido", "Al cerrar el pedido"),
        ("frecuencia_cliente", "Comportamiento", "pedidos", "cliente", "Hasta la fecha de corte"),
        ("porcentaje_custom", "Comportamiento", "%", "cliente", "Hasta la fecha de corte"),
        ("intervalo_medio_dias", "Comportamiento", "días", "cliente", "Hasta la fecha de corte"),
        ("unidades_modelo_mes", "Demanda", "pares", "modelo y mes", "Al cerrar el mes"),
        ("demanda_mes_anterior", "Demanda", "pares", "modelo y mes", "Antes de empezar el mes"),
        ("media_3_meses_previos", "Demanda", "pares", "modelo y mes", "Antes de empezar el mes"),
        ("talla_mas_solicitada", "Operaciones", "talla EU", "modelo", "Hasta la fecha de corte"),
    ]
    return pd.DataFrame(filas, columns=["variable", "familia", "unidad", "nivel", "disponible"])


def pedidos_unicos(datos):
    df = datos["pedidos"].copy()
    return con_metadatos(df, "01_pedidos_unicos", datos, datos.get("filtros", {}), len(datos["lineas"]), "pedidos_unicos")


def ventas_por_periodo(datos):
    pedidos, _ = ventas(datos)
    meses = pd.period_range(datos["pedidos"]["fecha_pedido"].min(), datos["pedidos"]["fecha_pedido"].max(),
                            freq="M")
    df = pedidos.groupby(pedidos["fecha_pedido"].dt.to_period("M").rename("mes")).agg(
        ingresos=("importe", "sum"),
        pares=("pares", "sum"),
        pedidos=("id_pedido", "nunique"),
    ).reindex(meses, fill_value=0)
    df.index.name = "mes"

    df["ingresos"] = df["ingresos"].round(2)
    df["ticket_medio"] = (df["ingresos"] / df["pedidos"].replace(0, np.nan)).round(2)
    df["variacion_mensual_pct"] = (df["ingresos"].pct_change() * 100).round(2)
    df["media_movil_3_previos"] = df["ingresos"].shift(1).rolling(3).mean().round(2)
    anterior = df["ingresos"].shift(12)
    df["variacion_interanual_pct"] = ((df["ingresos"] - anterior) / anterior.replace(0, np.nan) * 100).round(2)

    df["mes_completo"] = [mes.end_time < datos["fecha_corte"] for mes in df.index]
    df = df.reset_index()
    df["mes"] = df["mes"].astype(str)
    return con_metadatos(df, "02_ventas_por_periodo", datos, datos.get("filtros", {}), len(pedidos), "ventas_por_periodo")


def ranking(lineas, columna, etiqueta=None):
    df = lineas.groupby(columna).agg(
        ingresos=("importe_linea", "sum"),
        pares=("cantidad", "sum"),
        pedidos=("id_pedido", "nunique"),
    ).sort_values("ingresos", ascending=False).reset_index()
    if etiqueta:
        nombres = lineas.drop_duplicates(columna).set_index(columna)[etiqueta]
        df.insert(1, etiqueta, df[columna].map(nombres))

    total = df["ingresos"].sum()
    df["ingresos"] = df["ingresos"].round(2)
    df["ranking_euros"] = np.arange(1, len(df) + 1)
    df["ranking_pares"] = df["pares"].rank(ascending=False, method="min").astype(int)
    df["peso_pct"] = (df["ingresos"] / total * 100).round(2) if total else 0.0
    df["acumulado_pct"] = df["peso_pct"].cumsum().round(2)
    return df


def modelos_abc(datos):
    _, lineas = ventas(datos)
    df = ranking(lineas, "id_modelo", "modelo")

    sin_ventas = datos["modelos"][~datos["modelos"]["id_modelo"].isin(df["id_modelo"])]
    if not sin_ventas.empty:
        extra = sin_ventas[["id_modelo", "nombre"]].rename(columns={"nombre": "modelo"})
        extra = extra.assign(ingresos=0.0, pares=0, pedidos=0, ranking_euros=np.arange(len(df) + 1, len(df) + len(extra) + 1), ranking_pares=len(df) + 1, peso_pct=0.0, acumulado_pct=100.0)
        df = pd.concat([df, extra], ignore_index=True)

    acumulado_previo = df["acumulado_pct"] - df["peso_pct"]
    df["clase_abc"] = pd.cut(acumulado_previo, bins=[-np.inf, config.UMBRAL_ABC_A * 100, config.UMBRAL_ABC_B * 100, np.inf], labels=["A", "B", "C"], right=False).astype(str)
    return con_metadatos(df, "03_modelos_abc", datos, datos.get("filtros", {}), len(lineas), "modelos_abc")


def matriz_modelo_talla(datos, proporcion=False):
    _, lineas = ventas(datos)
    df = lineas.pivot_table(index="modelo", columns="talla", values="cantidad", aggfunc="sum", fill_value=0)
    nombre = "04_matriz_modelo_talla"
    if proporcion:
        df = (df.div(df.sum(axis=1), axis=0) * 100).round(2)
        nombre += "_pct"
    df.columns = [f"{t:g}" for t in df.columns]
    df = df.reset_index()
    return con_metadatos(df, nombre, datos, datos.get("filtros", {}), len(lineas), "matriz_modelo_talla")


def custom_vs_estandar(datos):
    pedidos = datos["pedidos"]
    filas = []
    for tipo in config.TIPOS_PEDIDO:
        del_tipo = pedidos[pedidos["tipo_pedido"] == tipo]
        venta = del_tipo[del_tipo["es_venta"]]
        filas.append({
            "tipo_pedido": tipo,
            "pedidos_totales": len(del_tipo),
            "pedidos_venta": len(venta),
            "pedidos_cancelados": int((del_tipo["estado"] == "CANCELADO").sum()),
            "pares": int(venta["pares"].sum()),
            "ingresos": round(venta["importe"].sum(), 2),
        })
    df = pd.DataFrame(filas)
    df["tasa_cancelacion_pct"] = (df["pedidos_cancelados"] / df["pedidos_totales"].replace(0, np.nan) * 100).round(2)
    df["ticket_medio"] = (df["ingresos"] / df["pedidos_venta"].replace(0, np.nan)).round(2)
    df["precio_medio_par"] = (df["ingresos"] / df["pares"].replace(0, np.nan)).round(2)
    for columna in ("pedidos_venta", "pares", "ingresos"):
        total = df[columna].sum()
        df[f"peso_{columna}_pct"] = (df[columna] / total * 100).round(2) if total else 0.0
    return con_metadatos(df, "05_custom_vs_estandar", datos, datos.get("filtros", {}), len(pedidos), "custom_vs_estandar")


def participacion_top(serie, fraccion=0.2):
    serie = serie.sort_values(ascending=False)
    total = serie.sum()
    if not total or serie.empty:
        return np.nan
    cuantos = max(1, int(np.ceil(len(serie) * fraccion)))
    return round(serie.iloc[:cuantos].sum() / total * 100, 2)


def calcular_kpis(datos):
    pedidos = datos["pedidos"]
    venta, lineas_venta = ventas(datos)
    ingresos = venta["importe"].sum()
    pares = venta["pares"].sum()
    custom = venta[venta["tipo_pedido"] == "CUSTOM"]

    filas = [
        ("pedidos_totales", len(pedidos), "pedidos", "nº de pedidos únicos en cualquier estado", "-"),
        ("pedidos_confirmados", int((pedidos["estado"] == "CONFIRMADO").sum()), "pedidos", "estado = CONFIRMADO", "-"),
        ("pedidos_pendientes", int((pedidos["estado"] == "BORRADOR").sum()), "pedidos", "estado = BORRADOR", "-"),
        ("pedidos_cancelados", int((pedidos["estado"] == "CANCELADO").sum()), "pedidos", "estado = CANCELADO", "-"),
        ("tasa_cancelacion_pct", round(dividir((pedidos["estado"] == "CANCELADO").sum(), len(pedidos)) * 100, 2), "%", "cancelados / pedidos totales", "pedidos totales"),
        ("pares_vendidos", int(pares), "pares", "Σ cantidad de líneas de pedidos de venta", "-"),
        ("ingresos_validos", round(ingresos, 2), config.MONEDA, "Σ cantidad × precio_unitario de pedidos de venta", "-"),
        ("ticket_medio", round(dividir(ingresos, len(venta)), 2), config.MONEDA, "ingresos / pedidos de venta", "pedidos de venta"),
        ("pares_por_pedido", round(dividir(pares, len(venta)), 2), "pares", "pares / pedidos de venta", "pedidos de venta"),
        ("precio_medio_par", round(dividir(ingresos, pares), 2), config.MONEDA, "ingresos / pares vendidos", "pares vendidos"),
        ("peso_custom_pedidos_pct", round(dividir(len(custom), len(venta)) * 100, 2), "%", "pedidos Custom de venta / pedidos de venta", "pedidos de venta"),
        ("peso_custom_pares_pct", round(dividir(custom["pares"].sum(), pares) * 100, 2), "%", "pares Custom / pares vendidos", "pares vendidos"),
        ("peso_custom_ingresos_pct", round(dividir(custom["importe"].sum(), ingresos) * 100, 2), "%", "ingresos Custom / ingresos válidos", "ingresos válidos"),
        ("clientes_compradores", int(venta["id_cliente"].nunique()), "clientes", "clientes distintos con algún pedido de venta", "-"),
        ("pareto_top20_modelos_pct", participacion_top(lineas_venta.groupby("id_modelo")["importe_linea"].sum()), "%", "ingresos del 20 % de modelos que más facturan / ingresos válidos", "ingresos válidos"),
        ("pareto_top20_clientes_pct", participacion_top(venta.groupby("id_cliente")["importe"].sum()), "%", "ingresos del 20 % de clientes que más compran / ingresos válidos", "ingresos válidos"),
    ]
    df = pd.DataFrame(filas, columns=["kpi", "valor", "unidad", "formula", "denominador"])
    return con_metadatos(df, "kpis", datos, datos.get("filtros", {}), len(pedidos), "calcular_kpis")