import plotly.graph_objects as go
import streamlit as st

import analiticas
import config
import refresco
from dashboard import interfaz

ETIQUETAS_KPI = {
    "ingresos_validos": "Ingresos válidos",
    "pares_vendidos": "Pares vendidos",
    "pedidos_confirmados": "Pedidos confirmados",
    "ticket_medio": "Ticket medio",
}
FORMATOS_KPI = {"ingresos_validos": interfaz.euros, "ticket_medio": interfaz.euros}
ESTADO_CALIDAD = {"CORRECTO": "correcto", "CON RECHAZOS": "alerta", "BLOQUEADO": "error"}
AVISO_REFRESCO = {refresco.CORRECTO: "info", refresco.SIN_CAMBIOS: "info", refresco.DATOS_INVALIDOS: "error",
                  refresco.ERROR_CARGA: "error"}


def barra_refresco(ultimo, valido):
    actualizado = f"{valido['comprobado']:%d/%m/%Y %H:%M:%S}" if valido else "ninguna"
    filas = interfaz.numero(valido["filas_validas"]) if valido else "0"
    interfaz.aviso(f"Refresco cada {config.INTERVALO_REFRESCO} · estado: {ultimo['estado']}",
                   f"Última comprobación {ultimo['comprobado']:%d/%m/%Y %H:%M:%S} · Última actualización válida "
                   f"{actualizado} · {filas} filas válidas · {ultimo['procedencia']} · procesado en "
                   f"{interfaz.numero(ultimo['duracion'], 2)} s", AVISO_REFRESCO[ultimo["estado"]])


def ciclo_fallido(ultimo, valido):
    interfaz.aviso("No se publican resultados de este ciclo",
                   f"{ultimo['estado'].capitalize()}: {ultimo['explicacion']}. Revisa la tabla de incidencias.",
                   "error")
    st.dataframe(ultimo["incidencias"], width="stretch", hide_index=True)
    if valido:
        interfaz.aviso(f"DESACTUALIZADO · datos de {valido['comprobado']:%d/%m/%Y %H:%M:%S}",
                       "Se sigue mostrando el último resultado válido. El panel se recupera solo en cuanto los CSV "
                       "vuelvan a estar bien.", "error")


def ver_datos(df, clave):
    if st.toggle("Ver los datos de este gráfico", key=f"ver_{clave}"):
        st.dataframe(df, width="stretch", hide_index=True)


def direccion(datos, filtrados, filtros):
    kpis = analiticas.calcular_kpis(filtrados).set_index("kpi")["valor"]
    interfaz.seccion("Resumen del periodo", "Ventas válidas = pedidos CONFIRMADOS. Borradores y cancelados solo "
                                            "cuentan como actividad.")
    interfaz.tarjetas_kpi([
        {"etiqueta": "Ingresos válidos", "valor": interfaz.euros(kpis["ingresos_validos"]),
         "detalle": "Σ cantidad × precio de pedidos confirmados", "destacado": True},
        {"etiqueta": "Pedidos confirmados", "valor": interfaz.numero(kpis["pedidos_confirmados"]),
         "detalle": f"de {interfaz.numero(kpis['pedidos_totales'])} pedidos en total"},
        {"etiqueta": "Ticket medio", "valor": interfaz.euros(kpis["ticket_medio"], 2),
         "detalle": "ingresos / pedidos confirmados"},
        {"etiqueta": "Pares vendidos", "valor": interfaz.numero(kpis["pares_vendidos"]),
         "detalle": f"{interfaz.numero(kpis['pares_por_pedido'], 1)} pares por pedido"},
        {"etiqueta": "Peso Custom", "valor": interfaz.porcentaje(kpis["peso_custom_ingresos_pct"]),
         "detalle": "de los ingresos válidos"},
        {"etiqueta": "Cancelación", "valor": interfaz.porcentaje(kpis["tasa_cancelacion_pct"]),
         "detalle": f"{interfaz.numero(kpis['pedidos_cancelados'])} pedidos cancelados"},
    ])

    mensual = analiticas.ventas_por_periodo(filtrados)
    columna_grafico, columna_comparacion = st.columns([1.6, 1], gap="large")
    with columna_grafico:
        interfaz.seccion("Evolución mensual", "Barras grises: mes en curso, todavía incompleto.")
        colores = [interfaz.COLORES["naranja"] if completo else interfaz.COLORES["rejilla"]
                   for completo in mensual["mes_completo"]]
        figura = go.Figure()
        figura.add_bar(x=mensual["mes"], y=mensual["ingresos"], marker_color=colores, name="Ingresos del mes",
                       hovertemplate="%{x}<br>%{y:,.0f} €<extra></extra>")
        figura.add_scatter(x=mensual["mes"], y=mensual["media_movil_3_previos"], mode="lines+markers",
                           line={"color": interfaz.COLORES["plata"], "dash": "dot"},
                           name="Media de los 3 meses previos", hovertemplate="%{y:,.0f} €<extra></extra>")
        figura.update_yaxes(title="EUR", tickformat=",.0f")
        figura.update_xaxes(type="category")
        interfaz.grafico(figura, "Ingresos válidos por mes")
        ver_datos(mensual, "mensual")

    with columna_comparacion:
        comparacion = analiticas.comparar_periodo_anterior(datos, filtros)
        interfaz.seccion("Frente al periodo anterior", "Sin periodo elegido se compara el último mes completo.")
        interfaz.comparativa(comparacion, ETIQUETAS_KPI, FORMATOS_KPI)


def producto(filtrados):
    abc = analiticas.modelos_abc(filtrados)
    con_ventas = abc[abc["ingresos"] > 0]
    tallas = analiticas.matriz_modelo_talla(filtrados).set_index("modelo")
    tipos = analiticas.custom_vs_estandar(filtrados)

    talla_top = tallas.sum().idxmax() if not tallas.empty else "—"
    interfaz.tarjetas_kpi([
        {"etiqueta": "Modelos con ventas", "valor": interfaz.numero(len(con_ventas)),
         "detalle": f"de {interfaz.numero(len(abc))} modelos del catálogo"},
        {"etiqueta": "Modelos clase A", "valor": interfaz.numero((con_ventas["clase_abc"] == "A").sum()),
         "detalle": f"generan hasta el {config.UMBRAL_ABC_A:.0%} de los ingresos", "destacado": True},
        {"etiqueta": "Modelo líder", "valor": con_ventas["modelo"].iloc[0] if not con_ventas.empty else "—",
         "detalle": interfaz.euros(con_ventas["ingresos"].iloc[0]) if not con_ventas.empty else ""},
        {"etiqueta": "Talla más vendida", "valor": talla_top,
         "detalle": f"{interfaz.numero(tallas[talla_top].sum())} pares" if not tallas.empty else ""},
    ])

    interfaz.seccion("Ranking ABC de modelos", "Barras: ingresos de cada modelo. Línea: % acumulado. A = hasta el "
                                               f"{config.UMBRAL_ABC_A:.0%}, B = hasta el {config.UMBRAL_ABC_B:.0%}.")
    colores = {"A": interfaz.COLORES["naranja"], "B": interfaz.COLORES["plata"], "C": interfaz.COLORES["rejilla"]}
    figura = go.Figure()
    figura.add_bar(x=con_ventas["modelo"], y=con_ventas["ingresos"], name="Ingresos",
                   marker_color=[colores[c] for c in con_ventas["clase_abc"]],
                   customdata=con_ventas[["clase_abc", "pares"]],
                   hovertemplate="%{x}<br>%{y:,.0f} € · clase %{customdata[0]}<br>%{customdata[1]} pares"
                                 "<extra></extra>")
    figura.add_scatter(x=con_ventas["modelo"], y=con_ventas["acumulado_pct"], yaxis="y2", mode="lines+markers",
                       name="% acumulado", line={"color": interfaz.COLORES["azul"]},
                       hovertemplate="%{y:.1f} % acumulado<extra></extra>")
    figura.add_hline(y=config.UMBRAL_ABC_A * 100, yref="y2", line_dash="dash",
                     line_color=interfaz.COLORES["naranja"])
    figura.update_layout(yaxis={"title": "EUR", "tickformat": ",.0f"},
                         yaxis2={"title": "% acumulado", "overlaying": "y", "side": "right", "range": [0, 105],
                                 "dtick": 20, "ticksuffix": " %", "showgrid": False})
    figura.update_xaxes(type="category")
    interfaz.grafico(figura, "Pareto de ingresos por modelo")
    ver_datos(abc, "abc")

    columna_tallas, columna_tipos = st.columns([1.3, 1], gap="large")
    with columna_tallas:
        interfaz.seccion("Tallas dentro de cada modelo", "Cada fila suma 100 %: compara tallas, no modelos.")
        porcentaje = analiticas.matriz_modelo_talla(filtrados, proporcion=True).set_index("modelo")
        interfaz.mapa_calor(porcentaje, "% de pares por talla", "Talla (EU)", "% del modelo")
        ver_datos(tallas.reset_index(), "tallas")

    with columna_tipos:
        interfaz.seccion("Custom frente a estándar", "Peso de cada tipo sobre el total de ventas válidas.")
        figura = go.Figure()
        for i, fila in tipos.iterrows():
            figura.add_bar(x=["Pedidos", "Pares", "Ingresos"], name=fila["tipo_pedido"],
                           y=[fila["peso_pedidos_venta_pct"], fila["peso_pares_pct"], fila["peso_ingresos_pct"]],
                           marker_color=interfaz.SERIE[i], texttemplate="%{y:.1f} %", textangle=0,
                           textposition="outside",
                           hovertemplate="%{x}: %{y:.1f} %<extra></extra>")
        figura.update_layout(barmode="group", yaxis={"title": "% del total", "range": [0, 105]})
        interfaz.grafico(figura, "Peso de cada tipo de pedido")
        st.dataframe(tipos[["tipo_pedido", "pedidos_venta", "pares", "ingresos", "ticket_medio", "precio_medio_par",
                            "tasa_cancelacion_pct"]], width="stretch", hide_index=True)


def clientes(datos, filtrados):
    rfm = analiticas.clientes_rfm(filtrados)
    compradores = rfm[rfm["frequency"] > 0]
    kpis = analiticas.calcular_kpis(filtrados).set_index("kpi")["valor"]

    interfaz.tarjetas_kpi([
        {"etiqueta": "Clientes con compras", "valor": interfaz.numero(len(compradores)),
         "detalle": f"{interfaz.numero(len(rfm) - len(compradores))} sin compras válidas"},
        {"etiqueta": "Concentración", "valor": interfaz.porcentaje(kpis["pareto_top20_clientes_pct"]),
         "detalle": "de los ingresos viene del 20 % de clientes", "destacado": True},
        {"etiqueta": "Gasto medio", "valor": interfaz.euros(compradores["monetary"].mean()),
         "detalle": "por cliente con compras"},
        {"etiqueta": "Pedidos por cliente", "valor": interfaz.numero(compradores["frequency"].mean(), 1),
         "detalle": "media de pedidos confirmados"},
    ])

    columna_ranking, columna_segmentos = st.columns(2, gap="large")
    with columna_ranking:
        interfaz.seccion("Clientes que más compran", "Top 10 por gasto en pedidos confirmados.")
        top = compradores.head(10).iloc[::-1]
        figura = go.Figure(go.Bar(x=top["monetary"], y=top["id_cliente"].map(lambda c: f"Cliente {c}"),
                                  orientation="h", marker_color=interfaz.COLORES["naranja"],
                                  customdata=top[["frequency", "segmento"]],
                                  hovertemplate="%{y}<br>%{x:,.0f} € · %{customdata[0]} pedidos<br>"
                                                "%{customdata[1]}<extra></extra>"))
        figura.update_xaxes(title="EUR", tickformat=",.0f")
        interfaz.grafico(figura, "Gasto por cliente")
        ver_datos(compradores, "ranking_clientes")

    with columna_segmentos:
        interfaz.seccion("Segmentos RFM", "Recency, frequency y monetary puntuados del 1 al 5.")
        segmentos = rfm.groupby("segmento").agg(clientes=("id_cliente", "count"),
                                                gasto=("monetary", "sum")).reset_index()
        segmentos["peso_gasto_pct"] = (segmentos["gasto"] / segmentos["gasto"].sum() * 100).round(1)
        segmentos = segmentos.sort_values("gasto")
        figura = go.Figure(go.Bar(x=segmentos["clientes"], y=segmentos["segmento"], orientation="h",
                                  marker_color=interfaz.COLORES["plata"], customdata=segmentos["peso_gasto_pct"],
                                  hovertemplate="%{y}: %{x} clientes<br>%{customdata:.1f} % del gasto"
                                                "<extra></extra>"))
        figura.update_xaxes(title="Clientes")
        interfaz.grafico(figura, "Clientes por segmento")
        ver_datos(segmentos, "segmentos")

    interfaz.seccion("Frecuencia frente a gasto", "Cada punto es un cliente, coloreado por su segmento RFM.")
    figura = go.Figure()
    for i, (segmento, grupo) in enumerate(compradores.groupby("segmento")):
        figura.add_scatter(x=grupo["frequency"], y=grupo["monetary"], mode="markers", name=segmento,
                           marker={"size": 11, "color": interfaz.SERIE[i % len(interfaz.SERIE)],
                                   "line": {"width": 1, "color": interfaz.COLORES["fondo"]}},
                           text=grupo["id_cliente"],
                           hovertemplate="Cliente %{text}<br>%{x} pedidos · %{y:,.0f} €<extra></extra>")
    figura.update_xaxes(title="Pedidos confirmados")
    figura.update_yaxes(title="Gasto (EUR)", tickformat=",.0f")
    interfaz.grafico(figura, "Clientes por pedidos y gasto")

    interfaz.seccion("Cohortes de compra", "% de clientes de cada mes de primera compra que vuelve a comprar.")
    tabla = analiticas.cohortes(filtrados)
    if tabla.empty:
        interfaz.aviso("Cohortes no calculables", tabla.attrs["estado"], "atencion")
    else:
        tabla = tabla.set_index("cohorte")
        interfaz.mapa_calor(tabla.drop(columns="clientes"), "Retención por cohorte", "Meses desde la primera compra",
                            "% que compra")
        ver_datos(tabla.reset_index(), "cohortes")

    interfaz.seccion("Agrupación automática (KMeans)", "Se calcula sobre todos los datos del origen, sin filtros.")
    agrupacion = analiticas.clustering_clientes(datos)
    if agrupacion["perfil"].empty:
        interfaz.aviso("Agrupación no calculable", agrupacion["estado"], "atencion")
        return
    st.caption(agrupacion["estado"])
    columna_perfil, columna_k = st.columns([2, 1], gap="large")
    with columna_perfil:
        st.dataframe(agrupacion["perfil"], width="stretch", hide_index=True)
        st.dataframe(agrupacion["comparacion_rfm"], width="stretch", hide_index=True)
    with columna_k:
        evaluacion = agrupacion["evaluacion"]
        figura = go.Figure(go.Bar(x=evaluacion["k"].astype(str), y=evaluacion["silhouette"],
                                  marker_color=[interfaz.COLORES["naranja"] if e else interfaz.COLORES["rejilla"]
                                                for e in evaluacion["elegido"]],
                                  hovertemplate="k = %{x}<br>silhouette %{y:.3f}<extra></extra>"))
        figura.update_xaxes(title="Número de grupos (k)")
        figura.update_yaxes(title="Silhouette")
        interfaz.grafico(figura, "Calidad de cada k")


def almacen(datos, filtrados):
    stock = analiticas.stock_cobertura(filtrados)
    interfaz.aviso("El stock es una foto, no un histórico",
                   f"Cantidades a fecha {stock['ultima_actualizacion'].max():%d/%m/%Y %H:%M}. La demanda es la de los "
                   f"últimos {config.DIAS_DEMANDA_RECIENTE} días; sin demanda la cobertura es N/D.")

    conteo = stock["alerta"].value_counts()
    interfaz.tarjetas_kpi([
        {"etiqueta": "Bajo mínimo", "valor": interfaz.numero(conteo.get("BAJO MÍNIMO", 0)),
         "detalle": "variantes y tallas por debajo del stock mínimo",
         "estado": "error" if conteo.get("BAJO MÍNIMO", 0) else "correcto"},
        {"etiqueta": "Riesgo de rotura", "valor": interfaz.numero(conteo.get("RIESGO DE ROTURA", 0)),
         "detalle": f"cobertura menor de {config.DIAS_COBERTURA_RIESGO} días",
         "estado": "alerta" if conteo.get("RIESGO DE ROTURA", 0) else "correcto"},
        {"etiqueta": "Sin demanda", "valor": interfaz.numero(conteo.get("SIN DEMANDA", 0)),
         "detalle": f"con stock y sin ventas en {config.DIAS_DEMANDA_RECIENTE} días"},
        {"etiqueta": "Pares en almacén", "valor": interfaz.numero(stock["stock"].sum()),
         "detalle": f"en {interfaz.numero(len(stock))} combinaciones de variante y talla"},
    ])

    por_modelo = stock.groupby("modelo").agg(stock=("stock", "sum"),
                                             demanda=("demanda_reciente", "sum")).reset_index()
    por_modelo = por_modelo.sort_values("demanda", ascending=False)
    interfaz.seccion("Stock y demanda reciente por modelo",
                     f"Demanda = pares vendidos en los últimos {config.DIAS_DEMANDA_RECIENTE} días.")
    figura = go.Figure()
    figura.add_bar(x=por_modelo["modelo"], y=por_modelo["stock"], name="Stock actual",
                   marker_color=interfaz.COLORES["rejilla"],
                   hovertemplate="%{x}<br>%{y} pares en stock<extra></extra>")
    figura.add_bar(x=por_modelo["modelo"], y=por_modelo["demanda"],
                   name=f"Demanda {config.DIAS_DEMANDA_RECIENTE} días", marker_color=interfaz.COLORES["naranja"],
                   hovertemplate="%{x}<br>%{y} pares vendidos<extra></extra>")
    figura.update_layout(barmode="group")
    figura.update_xaxes(type="category")
    figura.update_yaxes(title="Pares")
    interfaz.grafico(figura, "Stock frente a demanda")
    ver_datos(por_modelo, "stock_modelo")

    interfaz.seccion("Alertas por variante y talla")
    alertas = st.multiselect("Mostrar alertas", analiticas.ORDEN_ALERTAS,
                             default=[a for a in ("BAJO MÍNIMO", "RIESGO DE ROTURA") if a in conteo],
                             placeholder="Todas", key="alertas_almacen")
    tabla = stock[stock["alerta"].isin(alertas)] if alertas else stock
    st.dataframe(tabla[["modelo", "color", "talla", "stock", "stock_minimo", "demanda_reciente", "cobertura_texto",
                        "alerta"]], width="stretch", hide_index=True)


def calidad(carga, datos, carpeta):
    resumen = analiticas.calidad_datos(carga["resumen"], carga["incidencias"])
    interfaz.seccion("Semáforo por fichero", "Verde: todo válido · naranja: algún registro rechazado · rojo: "
                                             "incidencia bloqueante.")
    interfaz.tarjetas_kpi([
        {"etiqueta": fila["tabla"], "valor": interfaz.porcentaje(fila["porcentaje_calidad"]),
         "detalle": f"{interfaz.numero(fila['filas_validas'])} de {interfaz.numero(fila['filas_entrada'])} filas "
                    f"· {fila['estado'].lower()}",
         "estado": ESTADO_CALIDAD[fila["estado"]]}
        for _, fila in resumen.iterrows()
    ])

    columna_reglas, columna_sql = st.columns(2, gap="large")
    with columna_reglas:
        interfaz.seccion("Incidencias por regla")
        reglas = analiticas.incidencias_por_regla(carga["incidencias"])
        if reglas.empty:
            interfaz.aviso("Sin incidencias", "Todos los registros cumplen las 12 reglas de validación.")
        else:
            st.dataframe(reglas, width="stretch", hide_index=True)
            ver_datos(carga["incidencias"], "incidencias")

    with columna_sql:
        interfaz.seccion("Conciliación con PostgreSQL", "Cifras de Python frente a referencia_sql.csv.")
        conciliacion = analiticas.reconciliacion_sql(datos, carpeta)
        correctos = (conciliacion["estado"] == "OK").sum()
        if (conciliacion["estado"] == "SIN REFERENCIA").all():
            interfaz.aviso("Sin referencia SQL",
                           f"No hay {config.FICHERO_REFERENCIA_SQL} en la carpeta de este origen. Es lo normal con el "
                           "histórico sintético, que no viene de PostgreSQL.")
        else:
            tipo = "info" if correctos == len(conciliacion) else "atencion"
            interfaz.aviso(f"{correctos} de {len(conciliacion)} indicadores cuadran",
                           "OK = diferencia menor de 1 céntimo. DIFERENCIA = revisar si los CSV y la referencia se "
                           "exportaron a la vez.", tipo)
        st.dataframe(conciliacion, width="stretch", hide_index=True)

    interfaz.seccion("Ficheros leídos", f"Última ejecución válida: {carga['comprobado']:%d/%m/%Y %H:%M:%S}.")
    st.dataframe(carga["manifiesto"], width="stretch", hide_index=True)

    interfaz.seccion("Lo que estos datos no permiten afirmar")
    interfaz.lista_limitaciones(analiticas.limitaciones(datos)["no_puede_afirmarse"])


def prediccion(resultado, origen):
    interfaz.laboratorio("La predicción necesita al menos un año de histórico. Con datos reales aún no hay meses "
                         "suficientes, así que el método se demuestra con el histórico SINTÉTICO, que no representa "
                         "clientes reales.")
    if resultado is None:
        interfaz.aviso("Predicción pendiente", "Todavía no existe prediccion.py en el proyecto.", "atencion")
        return
    if resultado["metricas"].empty:
        interfaz.aviso("Predicción no calculable", resultado["estado"], "atencion")
        if origen == "REAL":
            st.caption("Cambia el origen de los datos a «Histórico sintético» en el panel lateral.")
        return

    metricas = resultado["metricas"].set_index("modelo")
    base, modelo = metricas.loc["baseline"], metricas.drop(index="baseline").iloc[0]
    mejora = modelo["mejora_mae_pct"]
    interfaz.tarjetas_kpi([
        {"etiqueta": "MAE baseline", "valor": interfaz.numero(base["mae"], 1),
         "detalle": "pares de error medio repitiendo el mes anterior"},
        {"etiqueta": "MAE modelo", "valor": interfaz.numero(modelo["mae"], 1),
         "detalle": metricas.index[1], "destacado": True},
        {"etiqueta": "Mejora sobre baseline", "valor": interfaz.porcentaje(mejora),
         "detalle": "reducción del MAE", "estado": "correcto" if mejora > 0 else "error"},
        {"etiqueta": "RMSE modelo", "valor": interfaz.numero(modelo["rmse"], 1),
         "detalle": f"baseline {interfaz.numero(base['rmse'], 1)}"},
    ])
    st.caption(resultado["estado"])

    serie = resultado["serie"]
    interfaz.seccion("Real frente a predicción", f"Pares de todos los modelos. Los últimos {config.MESES_PRUEBA} "
                                                  "meses no se usaron para entrenar.")
    figura = go.Figure()
    figura.add_scatter(x=serie["mes"], y=serie["real"], mode="lines+markers", name="Real",
                       line={"color": interfaz.COLORES["plata"], "width": 3})
    figura.add_scatter(x=serie["mes"], y=serie["baseline"], mode="lines+markers", name="Baseline (mes anterior)",
                       line={"color": interfaz.COLORES["azul"], "dash": "dash"})
    figura.add_scatter(x=serie["mes"], y=serie["prediccion"], mode="lines+markers", name="Modelo",
                       line={"color": interfaz.COLORES["naranja"], "width": 3})
    prueba = serie[serie["conjunto"] == "prueba"]["mes"]
    if not prueba.empty:
        figura.add_vrect(x0=prueba.iloc[0], x1=prueba.iloc[-1], fillcolor=interfaz.COLORES["rejilla"], opacity=0.5,
                         line_width=0, annotation_text="prueba", annotation_position="top left")
    figura.update_xaxes(type="category")
    figura.update_yaxes(title="Pares")
    interfaz.grafico(figura, "Pares vendidos por mes")

    interfaz.seccion("Error por modelo de zapatilla", "Ordenado de mayor a menor error del modelo.")
    st.dataframe(resultado["por_modelo"], width="stretch", hide_index=True)
    ver_datos(resultado["detalle"], "detalle_prediccion")
