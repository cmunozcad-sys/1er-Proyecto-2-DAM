import numpy as np
import pandas as pd

from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

import config
from pipeline import resumir_por_pedido


KPIS_COMPARABLES = ["ingresos_validos", "pares_vendidos", "pedidos_confirmados", "ticket_medio"]

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
    fecha_corte = datos.get("fecha_corte")
    ejecucion = datos.get("ejecucion") or pd.Timestamp.now()
    df.attrs = {
        "nombre": nombre,
        "origen": datos["origen"],
        "fecha_corte": str(fecha_corte.date()) if fecha_corte is not None else "-",
        "ejecucion": f"{ejecucion:%Y-%m-%d %H:%M:%S}",
        "filtros": {k: v for k, v in filtros.items() if v not in (None, [])},
        "filas_origen": int(filas_origen),
        "funcion": funcion,
        "reglas": f"Venta válida: estado en {config.ESTADOS_VENTA}",
    }
    return df


def preparar_datos(validas, lineas_enriquecidas, pedidos_unicos, origen, ejecucion=None):
    fecha_corte = pedidos_unicos["fecha_pedido"].max().normalize() + pd.Timedelta(days=1)
    return {
        "origen": origen,
        "fecha_corte": fecha_corte,
        "ejecucion": pd.Timestamp(ejecucion) if ejecucion is not None else pd.Timestamp.now(),
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


MESES_DEL_ANIO = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]


def matriz_modelo_mes(datos):
    demanda = demanda_modelo_mes(datos)
    demanda["modelo"] = demanda["id_modelo"].map(datos["modelos"].set_index("id_modelo")["nombre"])
    df = demanda.pivot_table(index="modelo", columns="mes", values="unidades_modelo_mes", aggfunc="sum", fill_value=0)
    df = df[df.sum(axis=1) > 0]
    df.columns.name = None
    df = df.reset_index()
    return con_metadatos(df, "13_matriz_modelo_mes", datos, datos.get("filtros", {}), len(demanda), "matriz_modelo_mes")


def productos_estacionales(datos):
    demanda = demanda_modelo_mes(datos)
    demanda = demanda[pd.PeriodIndex(demanda["mes"], freq="M").end_time < datos["fecha_corte"]]
    demanda = demanda[demanda.groupby("id_modelo")["unidades_modelo_mes"].cumsum() > 0]
    meses = demanda.groupby("id_modelo")["mes"].nunique()
    validos = meses[meses >= config.MESES_MINIMOS_ESTACIONALIDAD].index
    if validos.empty:
        df = con_metadatos(pd.DataFrame(), "14_productos_estacionales", datos, datos.get("filtros", {}), len(demanda), "productos_estacionales")
        df.attrs["estado"] = (f"NO CALCULABLE: ningún modelo tiene {config.MESES_MINIMOS_ESTACIONALIDAD} meses completos desde su primera venta. " "Usar el histórico sintético para demostrar el método.")
        return df

    demanda = demanda[demanda["id_modelo"].isin(validos)]
    media_mes = demanda.pivot_table(index="id_modelo", columns="mes_del_anio", values="unidades_modelo_mes", aggfunc="mean")
    indice = media_mes.div(media_mes.mean(axis=1), axis=0)

    df = pd.DataFrame({
        "modelo": indice.index.map(datos["modelos"].set_index("id_modelo")["nombre"]),
        "meses_historico": meses[indice.index],
        "mes_pico": [MESES_DEL_ANIO[m - 1] for m in indice.idxmax(axis=1)],
        "indice_pico": indice.max(axis=1).round(2),
        "mes_valle": [MESES_DEL_ANIO[m - 1] for m in indice.idxmin(axis=1)],
        "indice_valle": indice.min(axis=1).round(2),
    }, index=indice.index)
    df["es_estacional"] = df["indice_pico"] >= config.UMBRAL_ESTACIONALIDAD
    indice.columns = [MESES_DEL_ANIO[m - 1] for m in indice.columns]
    df = df.join(indice.round(2)).sort_values("indice_pico", ascending=False).reset_index()

    df = con_metadatos(df, "14_productos_estacionales", datos, datos.get("filtros", {}), len(demanda), "productos_estacionales")
    df.attrs["estado"] = (f"CALCULADO con {len(df)} modelos: {int(df['es_estacional'].sum())} son estacionales " f"(su mes pico vende al menos {config.UMBRAL_ESTACIONALIDAD} veces su media mensual).")
    return df


def cambios_mezcla_tallas(datos):
    _, lineas = ventas(datos)
    completos = [m for m in sorted(lineas["periodo"].unique()) if pd.Period(m, freq="M").end_time < datos["fecha_corte"]]
    n = config.MESES_MEZCLA_TALLAS
    if len(completos) < 2 * n:
        df = con_metadatos(pd.DataFrame(), "15_cambios_mezcla_tallas", datos, datos.get("filtros", {}), len(lineas), "cambios_mezcla_tallas")
        df.attrs["estado"] = (f"NO CALCULABLE: hay {len(completos)} meses completos con ventas y hacen falta {2 * n} " f"para comparar los últimos {n} con los {n} anteriores.")
        return df

    anteriores, recientes = completos[-2 * n:-n], completos[-n:]

    def reparto(periodos):
        pares = lineas[lineas["periodo"].isin(periodos)].groupby("talla")["cantidad"].sum()
        return pares / pares.sum() * 100

    df = pd.DataFrame({"pct_anterior": reparto(anteriores), "pct_reciente": reparto(recientes)}).fillna(0).round(2)
    df["diferencia_puntos"] = (df["pct_reciente"] - df["pct_anterior"]).round(2)
    df["cambio"] = np.where(df["diferencia_puntos"] >= config.UMBRAL_CAMBIO_TALLA, "SUBE", np.where(df["diferencia_puntos"] <= -config.UMBRAL_CAMBIO_TALLA, "BAJA", "ESTABLE"))
    df.index.name = "talla"
    df = df.reset_index()

    df = con_metadatos(df, "15_cambios_mezcla_tallas", datos, datos.get("filtros", {}), len(lineas), "cambios_mezcla_tallas")
    df.attrs["estado"] = (f"CALCULADO: {anteriores[0]} a {anteriores[-1]} frente a {recientes[0]} a {recientes[-1]}. " f"{int((df['cambio'] != 'ESTABLE').sum())} tallas cambian {config.UMBRAL_CAMBIO_TALLA} puntos o más.")
    return df


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

def puntuar(serie, invertir=False):
    if serie.empty:
        return serie
    posicion = serie.rank(method="average", pct=True)
    puntos = np.ceil(posicion * 5).clip(1, 5).astype(int)
    return 6 - puntos if invertir else puntos


def segmento_rfm(fila):
    r, f = fila["r"], fila["f"]
    if r >= 4 and f >= 4:
        return "Campeones"
    if f >= 4:
        return "Leales"
    if r <= 2 and f >= 3:
        return "En riesgo"
    if r >= 4 and f <= 2:
        return "Nuevos"
    if r <= 2 and f <= 2:
        return "Perdidos"
    return "Potenciales"


def clientes_rfm(datos):
    pedidos, _ = ventas(datos)
    df = pedidos.groupby("id_cliente").agg(
        tipo_cliente=("tipo_cliente", "first"),
        ultima_compra=("fecha_pedido", "max"),
        frequency=("id_pedido", "nunique"),
        monetary=("importe", "sum"),
    ).reset_index()
    df["recency_dias"] = (datos["fecha_corte"] - df["ultima_compra"]).dt.days
    df["monetary"] = df["monetary"].round(2)

    df["r"] = puntuar(df["recency_dias"], invertir=True)
    df["f"] = puntuar(df["frequency"])
    df["m"] = puntuar(df["monetary"])
    df["puntuacion_rfm"] = df["r"].astype(str) + df["f"].astype(str) + df["m"].astype(str)
    df["segmento"] = df.apply(segmento_rfm, axis=1) if not df.empty else []
    df = df.merge(variables_cliente(datos), on="id_cliente", how="left", validate="one_to_one")

    sin_compras = datos["clientes"][~datos["clientes"]["id_cliente"].isin(df["id_cliente"])]
    if not sin_compras.empty:
        extra = pd.DataFrame({"id_cliente": sin_compras["id_cliente"], "tipo_cliente": sin_compras["tipo"], "frequency": 0, "monetary": 0.0, "segmento": "Sin compras válidas"})
        df = pd.concat([df, extra], ignore_index=True)
    df = df.sort_values("monetary", ascending=False).reset_index(drop=True)
    return con_metadatos(df, "06_clientes_rfm", datos, datos.get("filtros", {}), len(pedidos), "clientes_rfm")


def cohortes(datos):
    pedidos, _ = ventas(datos)
    meses = pedidos.assign(mes=pedidos["fecha_pedido"].dt.to_period("M"))[["id_cliente", "mes"]].drop_duplicates()
    clientes, num_meses = meses["id_cliente"].nunique(), meses["mes"].nunique()
    if clientes < config.MINIMO_CLIENTES_COHORTES or num_meses < config.MESES_MINIMOS_COHORTES:
        df = con_metadatos(pd.DataFrame(), "07_cohortes", datos, datos.get("filtros", {}), len(pedidos), "cohortes")
        df.attrs["estado"] = (f"NO CALCULABLE: hay {clientes} clientes con compras en {num_meses} meses y hacen falta al menos " f"{config.MINIMO_CLIENTES_COHORTES} clientes y {config.MESES_MINIMOS_COHORTES} meses. Usar el histórico sintético para demostrar el método.")
        return df

    meses["cohorte"] = meses.groupby("id_cliente")["mes"].transform("min")
    meses["meses_desde_alta"] = (meses["mes"] - meses["cohorte"]).apply(lambda d: d.n)

    activos = meses.pivot_table(index="cohorte", columns="meses_desde_alta", values="id_cliente", aggfunc="nunique",
                                fill_value=0)
    tamano = activos[0] if 0 in activos.columns else pd.Series(dtype=int)
    df = (activos.div(tamano, axis=0) * 100).round(1)
    df.columns = [f"mes_{c}" for c in df.columns]
    df.insert(0, "clientes", tamano)
    df = df.reset_index()
    df["cohorte"] = df["cohorte"].astype(str)
    df = con_metadatos(df, "07_cohortes", datos, datos.get("filtros", {}), len(pedidos), "cohortes")
    df.attrs["estado"] = f"CALCULADO con {clientes} clientes en {num_meses} meses."
    return df


ORDEN_ALERTAS = ["BAJO MÍNIMO", "RIESGO DE ROTURA", "DESCATALOGADO CON STOCK", "SIN DEMANDA", "DESCATALOGADO", "OK"]


def alerta_stock(fila):
    if not fila["modelo_activo"]:
        return "DESCATALOGADO CON STOCK" if fila["stock"] > 0 else "DESCATALOGADO"
    if fila["stock"] < fila["stock_minimo"]:
        return "BAJO MÍNIMO"
    if pd.notna(fila["cobertura_dias"]) and fila["cobertura_dias"] < config.DIAS_COBERTURA_RIESGO:
        return "RIESGO DE ROTURA"
    if fila["demanda_reciente"] == 0 and fila["stock"] > 0:
        return "SIN DEMANDA"
    return "OK"


def stock_cobertura(datos):
    _, lineas = ventas(datos)
    inicio = datos["fecha_corte"] - pd.Timedelta(days=config.DIAS_DEMANDA_RECIENTE)
    recientes = lineas[lineas["fecha_pedido"] >= inicio]
    demanda = recientes.groupby(["id_variante", "talla"])["cantidad"].sum().rename("demanda_reciente")

    modelos = datos["modelos"][["id_modelo", "nombre", "activo"]].rename(
        columns={"nombre": "modelo", "activo": "modelo_activo"})
    df = datos["stock"].rename(columns={"cantidad": "stock"}).merge(modelos, on="id_modelo", how="left", validate="many_to_one")
    df["modelo_activo"] = df["modelo_activo"].fillna(True).astype(bool)
    df = df.merge(demanda.reset_index(), on=["id_variante", "talla"], how="left", validate="one_to_one")
    df["demanda_reciente"] = df["demanda_reciente"].fillna(0).astype(int)
    df["demanda_diaria"] = (df["demanda_reciente"] / config.DIAS_DEMANDA_RECIENTE).round(3)
    df["cobertura_dias"] = (df["stock"] / df["demanda_diaria"].replace(0, np.nan)).round(1)
    df["cobertura_semanas"] = (df["cobertura_dias"] / 7).round(1)
    df["alerta"] = df.apply(alerta_stock, axis=1)
    df["cobertura_texto"] = df["cobertura_semanas"].map(lambda s: "N/D" if pd.isna(s) else f"{s:g} semanas")

    columnas = ["id_modelo", "modelo", "id_variante", "color", "talla", "stock", "stock_minimo", "demanda_reciente",
                "demanda_diaria", "cobertura_dias", "cobertura_semanas", "cobertura_texto", "alerta",
                "ultima_actualizacion"]
    df["alerta"] = pd.Categorical(df["alerta"], categories=ORDEN_ALERTAS, ordered=True)
    df = df[columnas].sort_values(["alerta", "cobertura_dias"]).reset_index(drop=True)
    df["alerta"] = df["alerta"].astype(str)
    return con_metadatos(df, "08_stock_cobertura", datos, datos.get("filtros", {}), len(datos["stock"]), "stock_cobertura")


def calidad_datos(resumen, incidencias):
    conteo = incidencias.pivot_table(index="tabla", columns="gravedad", values="regla", aggfunc="count", fill_value=0)
    df = resumen.merge(conteo, left_on="tabla", right_index=True, how="left")
    for gravedad in ("BLOQUEANTE", "RECUPERABLE", "ADVERTENCIA"):
        df[gravedad.lower()] = df[gravedad].fillna(0).astype(int) if gravedad in df else 0
    df["estado"] = np.where(df["bloqueante"] > 0, "BLOQUEADO",
                            np.where(df["filas_rechazadas"] > 0, "CON RECHAZOS", "CORRECTO"))
    return df[["tabla", "filas_entrada", "filas_validas", "filas_rechazadas", "porcentaje_calidad", "bloqueante", "recuperable", "advertencia", "estado"]]


def incidencias_por_regla(incidencias):
    return incidencias.groupby(["regla", "gravedad", "tabla", "descripcion"]).size().rename(
        "registros").reset_index().sort_values(["regla", "tabla"])


def limites_iqr(serie):
    q1, q3 = serie.quantile(0.25), serie.quantile(0.75)
    rango = q3 - q1
    return q1 - config.FACTOR_IQR * rango, q3 + config.FACTOR_IQR * rango


def explicar_pedido(fila):
    if fila["tipo_pedido"] == "CUSTOM" and fila["tipo_cliente"] in ("CLUB", "EQUIPO"):
        return "Pedido Custom de club o equipo: volumen grande esperable"
    return "Revisar con negocio"


def anomalias(datos):
    pedidos, lineas = ventas(datos)
    filas = []

    for variable in ("importe", "pares"):
        if len(pedidos) < 4:
            break
        inferior, superior = limites_iqr(pedidos[variable])
        atipicos = pedidos[(pedidos[variable] < inferior) | (pedidos[variable] > superior)]
        for _, fila in atipicos.iterrows():
            filas.append({"nivel": "pedido", "registro": fila["id_pedido"], "variable": variable, "valor": fila[variable], "limite_inferior": round(inferior, 2), "limite_superior": round(superior, 2), "explicacion": explicar_pedido(fila)})

    for id_modelo, grupo in lineas.groupby("id_modelo"):
        if len(grupo) < 4:
            continue
        inferior, superior = limites_iqr(grupo["precio_unitario"])
        atipicos = grupo[(grupo["precio_unitario"] < inferior) | (grupo["precio_unitario"] > superior)]
        for _, fila in atipicos.iterrows():
            explicacion = ("Recargo de personalización" if fila["personalizada"] else "Precio distinto al habitual del modelo: posible promoción")
            filas.append({"nivel": "linea", "registro": fila["id_linea"], "variable": f"precio_unitario ({fila['modelo']})", "valor": fila["precio_unitario"], "limite_inferior": round(inferior, 2), "limite_superior": round(superior, 2), "explicacion": explicacion})

    columnas = ["nivel", "registro", "variable", "valor", "limite_inferior", "limite_superior", "explicacion"]
    df = pd.DataFrame(filas, columns=columnas)
    df["decision"] = "Se conserva y se marca"
    return con_metadatos(df, "10_anomalias", datos, datos.get("filtros", {}), len(lineas), "anomalias")


def margen(datos):
    _, lineas = ventas(datos)
    df = ranking(lineas, "id_modelo", "modelo")[["id_modelo", "modelo", "ingresos", "pares"]]
    df["coste"] = "NO DISPONIBLE"
    df["margen"] = np.nan
    df["estado"] = "NO CALCULABLE: el contrato de datos no incluye coste unitario"
    return con_metadatos(df, "11_margen", datos, datos.get("filtros", {}), len(lineas), "margen")


def indicadores_conciliacion(datos):
    pedidos, lineas = datos["pedidos"], datos["lineas"]
    venta, lineas_venta = ventas(datos)
    del_mes = venta[venta["fecha_pedido"].dt.to_period("M").astype(str) == config.MES_CONCILIACION]
    de_talla = lineas_venta[lineas_venta["talla"] == config.TALLA_CONCILIACION]
    return {
        "pedidos_totales": len(pedidos),
        "lineas_totales": len(lineas),
        "pedidos_confirmados": len(venta),
        "pares_vendidos": int(venta["pares"].sum()),
        "ingresos_validos": round(venta["importe"].sum(), 2),
        f"ingresos_{config.MES_CONCILIACION}": round(del_mes["importe"].sum(), 2),
        f"pares_talla_{config.TALLA_CONCILIACION}": int(de_talla["cantidad"].sum()),
    }


def reconciliacion_sql(datos, carpeta):
    ruta = carpeta / config.FICHERO_REFERENCIA_SQL
    referencia = {}
    if ruta.exists():
        tabla = pd.read_csv(ruta, dtype={"indicador": str})
        referencia = dict(zip(tabla["indicador"], tabla["valor_sql"]))

    filas = []
    for indicador, valor in indicadores_conciliacion(datos).items():
        sql = referencia.get(indicador)
        if sql is None:
            estado, diferencia = "SIN REFERENCIA", np.nan
        else:
            diferencia = round(valor - float(sql), 2)
            estado = "OK" if abs(diferencia) < 0.01 else "DIFERENCIA"
        filas.append({"indicador": indicador, "valor_python": valor, "valor_sql": sql, "diferencia": diferencia, "estado": estado})
    df = pd.DataFrame(filas)
    return con_metadatos(df, "12_reconciliacion_sql", datos, {}, len(datos["pedidos"]), "reconciliacion_sql")

def describir(serie):
    serie = serie.dropna()
    if serie.empty:
        return {}
    moda = serie.mode()
    q1, q3 = serie.quantile(0.25), serie.quantile(0.75)
    media, mediana = serie.mean(), serie.median()
    return {
        "n": len(serie),
        "media": round(media, 2),
        "mediana": round(mediana, 2),
        "moda": round(moda.iloc[0], 2) if len(moda) < len(serie) else np.nan,
        "desviacion": round(serie.std(), 2) if len(serie) > 1 else np.nan,
        "minimo": round(serie.min(), 2),
        "p25": round(q1, 2),
        "p75": round(q3, 2),
        "p90": round(serie.quantile(0.90), 2),
        "maximo": round(serie.max(), 2),
        "iqr": round(q3 - q1, 2),
        "representativo": "mediana" if mediana and abs(media - mediana) / abs(mediana) > 0.2 else "media",
    }


def estadisticos(datos):
    pedidos, _ = ventas(datos)
    variables = {"importe": "EUR por pedido", "pares": "pares por pedido", "precio_medio_par": "EUR por par"}
    filas = []
    for variable, unidad in variables.items():
        grupos = [("TODOS", pedidos)] + [(tipo, pedidos[pedidos["tipo_pedido"] == tipo]) for tipo in config.TIPOS_PEDIDO]
        for grupo, df in grupos:
            resumen = describir(df[variable])
            if resumen:
                filas.append({"variable": variable, "unidad": unidad, "grupo": grupo, **resumen})
    df = pd.DataFrame(filas)
    return con_metadatos(df, "estadisticos", datos, datos.get("filtros", {}), len(pedidos), "estadisticos")


def bootstrap_diferencia(a, b, estadistico, semilla=config.SEMILLA, repeticiones=config.REPETICIONES_BOOTSTRAP):
    rng = np.random.default_rng(semilla)
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    diferencias = np.empty(repeticiones)
    for i in range(repeticiones):
        diferencias[i] = estadistico(rng.choice(a, len(a))) - estadistico(rng.choice(b, len(b)))
    return np.percentile(diferencias, [2.5, 97.5])


def contrastar(hipotesis, metrica, grupo_a, a, grupo_b, b, estadistico, sentido="mayor"):
    fila = {"hipotesis": hipotesis, "metrica": metrica, "grupo_a": grupo_a, "n_a": len(a), "grupo_b": grupo_b,
            "n_b": len(b)}
    if min(len(a), len(b)) < config.MUESTRA_MINIMA:
        return {**fila, "valor_a": np.nan, "valor_b": np.nan, "diferencia": np.nan, "ic95_inferior": np.nan,
                "ic95_superior": np.nan, "conclusion": "EVIDENCIA INSUFICIENTE",
                "explicacion": f"Hacen falta al menos {config.MUESTRA_MINIMA} casos en cada grupo."}

    valor_a, valor_b = estadistico(np.asarray(a, dtype=float)), estadistico(np.asarray(b, dtype=float))
    inferior, superior = bootstrap_diferencia(a, b, estadistico)
    if inferior > 0 if sentido == "mayor" else superior < 0:
        conclusion = "APOYADA"
        explicacion = "El intervalo del 95 % no incluye el 0: la diferencia es consistente en los remuestreos."
    elif inferior <= 0 <= superior:
        conclusion = "EVIDENCIA INSUFICIENTE"
        explicacion = "El intervalo del 95 % incluye el 0: la diferencia podría deberse al azar."
    else:
        conclusion = "NO APOYADA"
        explicacion = "La diferencia va en sentido contrario al planteado."
    return {**fila, "valor_a": round(valor_a, 4), "valor_b": round(valor_b, 4),
            "diferencia": round(valor_a - valor_b, 4), "ic95_inferior": round(inferior, 4),
            "ic95_superior": round(superior, 4), "conclusion": conclusion, "explicacion": explicacion}


def hipotesis(datos):
    pedidos = datos["pedidos"]
    venta, _ = ventas(datos)
    cerrados = pedidos[pedidos["estado"] != "BORRADOR"]

    custom = venta.loc[venta["tipo_pedido"] == "CUSTOM", "importe"]
    estandar = venta.loc[venta["tipo_pedido"] == "ESTANDAR", "importe"]
    h1 = contrastar("H1. La mediana del importe de un pedido Custom es mayor que la de un pedido estándar",
                    "mediana del importe por pedido (EUR)", "CUSTOM", custom, "ESTANDAR", estandar, np.median)

    cancelado = cerrados["estado"] == "CANCELADO"
    h2 = contrastar("H2. Los pedidos Custom se cancelan con más frecuencia que los estándar",
                    "proporción de cancelados entre pedidos cerrados",
                    "CUSTOM", cancelado[cerrados["tipo_pedido"] == "CUSTOM"].astype(float),
                    "ESTANDAR", cancelado[cerrados["tipo_pedido"] == "ESTANDAR"].astype(float), np.mean)

    meses = ventas_por_periodo(datos)
    completos = meses[meses["mes_completo"]].tail(3)
    anteriores = meses[meses["mes"].isin((pd.PeriodIndex(completos["mes"], freq="M") - 12).astype(str))]
    actual = venta[venta["periodo"].isin(completos["mes"])]["importe"]
    previo = venta[venta["periodo"].isin(anteriores["mes"])]["importe"]
    if len(anteriores) < len(completos) or len(completos) < 3:
        previo = previo.iloc[:0]
    h3 = contrastar("H3. El importe medio por pedido de los últimos 3 meses supera al de los mismos meses del año "
                    "anterior", "media del importe por pedido (EUR)", "últimos 3 meses", actual,
                    "mismos meses año anterior", previo, np.mean)

    df = pd.DataFrame([h1, h2, h3])
    return con_metadatos(df, "hipotesis", datos, datos.get("filtros", {}), len(pedidos), "hipotesis")


def limitaciones(datos):
    venta, _ = ventas(datos)
    meses = datos["pedidos"]["periodo"].nunique()
    filas = [
        "Una diferencia entre grupos no demuestra que una variable cause la otra: solo describe lo observado.",
        "No puede calcularse beneficio ni margen: el contrato de datos no incluye coste unitario.",
        "El stock es una foto en la fecha de corte; no permite saber cuánto stock hubo en meses anteriores.",
    ]
    if datos["origen"] != "REAL":
        filas.append("Los datos son SINTÉTICOS: sirven para probar los métodos, no son evidencia de clientes reales.")
    if len(venta) < 30:
        filas.append(f"Con solo {len(venta)} pedidos de venta no se pueden generalizar tendencias ni comparar grupos " "con fiabilidad.")
    if meses < 13:
        filas.append(f"Con {meses} meses de histórico no se puede medir estacionalidad ni comparar con el año anterior.")
    df = pd.DataFrame({"no_puede_afirmarse": filas})
    return con_metadatos(df, "limitaciones", datos, datos.get("filtros", {}), len(venta), "limitaciones")


def ventana_actual(datos, filtros):
    if filtros.get("fecha_desde") is not None and filtros.get("fecha_hasta") is not None:
        return pd.Timestamp(filtros["fecha_desde"]), pd.Timestamp(filtros["fecha_hasta"])
    meses = ventas_por_periodo(datos)
    completos = meses[meses["mes_completo"]]
    ultimo = pd.Period(completos["mes"].iloc[-1] if not completos.empty else meses["mes"].iloc[-1], freq="M")
    return ultimo.start_time, ultimo.end_time.normalize()


def comparar_periodo_anterior(datos, filtros=None):
    filtros = {**FILTROS_VACIOS, **(filtros or {})}
    desde, hasta = ventana_actual(datos, filtros)
    meses_completos = desde.is_month_start and (hasta + pd.Timedelta(days=1)).is_month_start
    if meses_completos:
        meses = (hasta.to_period("M") - desde.to_period("M")).n + 1
        previo_desde = desde - pd.DateOffset(months=meses)
        previo_hasta = desde - pd.Timedelta(days=1)
    else:
        previo_hasta = desde - pd.Timedelta(days=1)
        previo_desde = previo_hasta - pd.Timedelta(days=(hasta - desde).days)

    actual = calcular_kpis(aplicar_filtros(datos, {**filtros, "fecha_desde": desde, "fecha_hasta": hasta}))
    anterior = calcular_kpis(aplicar_filtros(datos, {**filtros, "fecha_desde": previo_desde, "fecha_hasta": previo_hasta}))
    df = actual[["kpi", "valor", "unidad"]].rename(columns={"valor": "actual"}).merge(
        anterior[["kpi", "valor"]].rename(columns={"valor": "anterior"}), on="kpi", validate="one_to_one")
    df = df[df["kpi"].isin(KPIS_COMPARABLES)].reset_index(drop=True)
    df["variacion_pct"] = ((df["actual"] - df["anterior"]) / df["anterior"].replace(0, np.nan) * 100).round(2)
    df["periodo_actual"] = f"{desde:%Y-%m-%d} a {hasta:%Y-%m-%d}"
    df["periodo_anterior"] = f"{previo_desde:%Y-%m-%d} a {previo_hasta:%Y-%m-%d}"
    return con_metadatos(df, "comparacion_periodo_anterior", datos, filtros, len(datos["pedidos"]), "comparar_periodo_anterior")

VARIABLES_CLUSTER = ["recency_dias", "frequency", "monetary", "porcentaje_custom"]


def nombrar_cluster(centro):
    if centro["recency_dias"] > 0.5:
        return "Inactivos o en riesgo"
    if centro["monetary"] > 0.5 and centro["frequency"] > 0.5:
        return "Grandes cuentas recurrentes"
    if centro["frequency"] > 0.5:
        return "Compradores frecuentes de estándar"
    if centro["porcentaje_custom"] > 0.5:
        return "Compradores de personalización"
    if centro["monetary"] < 0 and centro["frequency"] < 0:
        return "Ocasionales de bajo gasto"
    return "Regulares"


def clustering_clientes(datos):
    rfm = clientes_rfm(datos)
    compradores = rfm[rfm["frequency"] > 0].dropna(subset=VARIABLES_CLUSTER).reset_index(drop=True)
    vacio = {"evaluacion": pd.DataFrame(), "perfil": pd.DataFrame(), "asignacion": pd.DataFrame(), "comparacion_rfm": pd.DataFrame()}
    for nombre, df in vacio.items():
        con_metadatos(df, f"clusters_{nombre}", datos, datos.get("filtros", {}), len(compradores), "clustering_clientes")

    if len(compradores) < config.MINIMO_CLIENTES_CLUSTER:
        estado = (f"NO CALCULABLE: hay {len(compradores)} clientes con compras y hacen falta al menos " f"{config.MINIMO_CLIENTES_CLUSTER}. Usar el histórico sintético para demostrar el método.")
        return {**vacio, "estado": estado}

    variables = compradores[VARIABLES_CLUSTER].copy()
    variables["frequency"] = np.log1p(variables["frequency"])
    variables["monetary"] = np.log1p(variables["monetary"])
    escaladas = StandardScaler().fit_transform(variables)

    evaluacion = []
    for k in config.VALORES_K:
        if k >= len(compradores):
            continue
        modelo = KMeans(n_clusters=k, n_init=10, random_state=config.SEMILLA).fit(escaladas)
        evaluacion.append({"k": k, "silhouette": round(silhouette_score(escaladas, modelo.labels_), 4), "inercia": round(modelo.inertia_, 2)})
    evaluacion = pd.DataFrame(evaluacion)
    mejor_k = int(evaluacion.loc[evaluacion["silhouette"].idxmax(), "k"])
    evaluacion["elegido"] = evaluacion["k"] == mejor_k

    modelo = KMeans(n_clusters=mejor_k, n_init=10, random_state=config.SEMILLA).fit(escaladas)
    compradores["cluster"] = modelo.labels_
    centros = pd.DataFrame(modelo.cluster_centers_, columns=VARIABLES_CLUSTER)
    nombres = {}
    for cluster, centro in centros.iterrows():
        nombre = nombrar_cluster(centro)
        repetidos = sum(1 for n in nombres.values() if n.startswith(nombre))
        nombres[cluster] = nombre if not repetidos else f"{nombre} {repetidos + 1}"
    compradores["nombre_cluster"] = compradores["cluster"].map(nombres)

    total_ingresos = compradores["monetary"].sum()
    perfil = compradores.groupby(["cluster", "nombre_cluster"]).agg(
        clientes=("id_cliente", "count"),
        recency_media_dias=("recency_dias", "mean"),
        pedidos_medios=("frequency", "mean"),
        gasto_medio=("monetary", "mean"),
        gasto_mediano=("monetary", "median"),
        porcentaje_custom_medio=("porcentaje_custom", "mean"),
        ingresos=("monetary", "sum"),
    ).reset_index()
    perfil["peso_clientes_pct"] = (perfil["clientes"] / len(compradores) * 100).round(2)
    perfil["peso_ingresos_pct"] = (perfil["ingresos"] / total_ingresos * 100).round(2)
    perfil = perfil.round(2)

    comparacion = pd.crosstab(compradores["nombre_cluster"], compradores["segmento"])
    comparacion = comparacion.reset_index().rename(columns={"nombre_cluster": "cluster"})

    asignacion = compradores[["id_cliente", "tipo_cliente", "cluster", "nombre_cluster", "segmento"] + VARIABLES_CLUSTER]
    estado = (f"CALCULADO con {len(compradores)} clientes y k = {mejor_k} (mayor silhouette). " "Un clúster es un grupo matemático de clientes parecidos en estas 4 variables; no equivale " "automáticamente a un segmento comercial.")

    resultado = {"evaluacion": evaluacion, "perfil": perfil, "asignacion": asignacion, "comparacion_rfm": comparacion, "estado": estado}
    for nombre in ("evaluacion", "perfil", "asignacion", "comparacion_rfm"):
        con_metadatos(resultado[nombre], f"clusters_{nombre}", datos, datos.get("filtros", {}), len(compradores), "clustering_clientes")
    return resultado