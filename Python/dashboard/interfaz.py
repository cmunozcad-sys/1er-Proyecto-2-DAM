# Componentes visuales del dashboard: estilos, formatos, tarjetas, avisos y gráficos

import base64
import html
from pathlib import Path

import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

# Carpeta con el CSS y el logo
RECURSOS = Path(__file__).resolve().parent

# Paleta del dashboard
COLORES = {
    "fondo": "rgb(10, 10, 12)",
    "superficie": "rgb(22, 22, 26)",
    "rejilla": "rgb(40, 40, 46)",
    "texto": "rgb(235, 235, 240)",
    "suave": "rgb(150, 150, 160)",
    "plata": "rgb(219, 219, 219)",
    "naranja": "rgb(255, 165, 0)",
    "exito": "rgb(110, 200, 120)",
    "error": "rgb(240, 90, 90)",
    "azul": "rgb(90, 160, 255)",
}
# Colores de las series de los gráficos
SERIE = [COLORES["naranja"], COLORES["plata"], COLORES["azul"], COLORES["exito"], "rgb(190, 120, 255)", COLORES["error"], "rgb(120, 120, 130)"]

# Plantilla de Plotly con el estilo oscuro del panel
pio.templates["sneaker"] = go.layout.Template(layout=go.Layout(
    font={"family": "Inter, sans-serif", "color": COLORES["texto"], "size": 13},
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    colorway=SERIE,
    separators=",.",
    margin={"l": 10, "r": 10, "t": 50, "b": 10},
    hoverlabel={"bgcolor": COLORES["superficie"], "bordercolor": COLORES["naranja"],
                "font": {"color": COLORES["texto"]}},
    xaxis={"gridcolor": COLORES["rejilla"], "linecolor": COLORES["rejilla"], "zeroline": False},
    yaxis={"gridcolor": COLORES["rejilla"], "linecolor": COLORES["rejilla"], "zeroline": False},
    legend={"orientation": "h", "y": -0.18, "x": 0, "bgcolor": "rgba(0,0,0,0)"},
    title={"font": {"family": "Montserrat, sans-serif", "size": 15, "color": COLORES["plata"]}, "x": 0},
))


# Importe en formato español (1.234 €); una raya si no hay dato
def euros(valor, decimales=0):
    if valor is None or valor != valor:
        return "—"
    return f"{valor:,.{decimales}f} €".replace(",", "X").replace(".", ",").replace("X", ".")


# Número en formato español (1.234,5); una raya si no hay dato
def numero(valor, decimales=0):
    if valor is None or valor != valor:
        return "—"
    return f"{valor:,.{decimales}f}".replace(",", "X").replace(".", ",").replace("X", ".")


# Porcentaje en formato español; una raya si no hay dato
def porcentaje(valor, decimales=1):
    if valor is None or valor != valor:
        return "—"
    return f"{valor:,.{decimales}f} %".replace(",", "X").replace(".", ",").replace("X", ".")


# Carga dashboard.css en la página
def cargar_estilos():
    st.html(f"<style>{(RECURSOS / 'dashboard.css').read_text(encoding='utf-8')}</style>")


# Cabecera con logo, insignia de datos reales o sintéticos, fecha de corte y última carga
def cabecera(origen, fecha_corte, ultima_carga):
    clase = "insignia--real" if origen == "REAL" else "insignia--sintetico"
    texto = "Datos reales" if origen == "REAL" else "Datos sintéticos"
    logo = base64.b64encode((RECURSOS / "logo.png").read_bytes()).decode()
    st.html(f"""
    <header class="cabecera">
        <img class="cabecera__logo" src="data:image/png;base64,{logo}" alt="Sneaker Factory">
        <div class="cabecera__textos">
            <h1 class="cabecera__titulo">Sneaker Factory</h1>
            <p class="cabecera__subtitulo">Panel de datos de producción y ventas</p>
        </div>
        <div class="cabecera__estado">
            <span class="insignia {clase}"><span class="insignia__punto"></span>{texto}</span>
            <span class="cabecera__dato">Fecha de corte {fecha_corte:%d/%m/%Y} · cargado {ultima_carga:%H:%M:%S}</span>
        </div>
    </header>
    """)


# Título y subtítulo de una sección
def seccion(titulo, subtitulo=""):
    detalle = f'<p class="seccion__subtitulo">{html.escape(subtitulo)}</p>' if subtitulo else ""
    st.html(f'<div class="seccion"><h2 class="seccion__titulo">{html.escape(titulo)}</h2>{detalle}</div>')


# Rejilla de tarjetas con los KPIs
def tarjetas_kpi(tarjetas):
    bloques = []
    for tarjeta in tarjetas:
        clase = "kpi kpi--destacado" if tarjeta.get("destacado") else "kpi"
        if tarjeta.get("estado"):
            clase = f"kpi kpi--{tarjeta['estado']}"
        bloques.append(f"""
        <article class="{clase}">
            <p class="kpi__etiqueta">{html.escape(tarjeta['etiqueta'])}</p>
            <p class="kpi__valor">{html.escape(tarjeta['valor'])}</p>
            <p class="kpi__detalle">{html.escape(tarjeta.get('detalle', ''))}</p>
        </article>""")
    st.html(f'<section class="rejilla-kpi">{"".join(bloques)}</section>')


# Tabla del periodo actual frente al anterior, con flecha y % de cambio en verde, rojo o neutro
def comparativa(tabla, etiquetas, formatos):
    filas = []
    for _, fila in tabla.iterrows():
        formato = formatos.get(fila["kpi"], numero)
        cambio = fila["variacion_pct"]
        if cambio is None or cambio != cambio:
            variacion = '<span class="variacion variacion--neutra">sin dato</span>'
        else:
            clase = "variacion--sube" if cambio > 0 else "variacion--baja" if cambio < 0 else "variacion--neutra"
            flecha = "▲" if cambio > 0 else "▼" if cambio < 0 else "="
            texto = f"{abs(cambio):,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")
            variacion = f'<span class="variacion {clase}">{flecha} {texto} %</span>'
        filas.append(f"""
        <div class="comparativa__fila">
            <span>{html.escape(etiquetas.get(fila['kpi'], fila['kpi']))}</span>
            <span class="comparativa__numero">{formato(fila['actual'])}</span>
            <span class="comparativa__numero">{formato(fila['anterior'])}</span>
            {variacion}
        </div>""")
    st.html(f"""
    <section class="comparativa">
        <p class="comparativa__periodos">Actual: {tabla['periodo_actual'].iloc[0]}<br>
        Anterior: {tabla['periodo_anterior'].iloc[0]}</p>
        <div class="comparativa__fila comparativa__fila--cabecera">
            <span>Indicador</span><span class="comparativa__numero">Actual</span>
            <span class="comparativa__numero">Anterior</span><span class="comparativa__numero">Cambio</span>
        </div>
        {"".join(filas)}
    </section>
    """)


# Caja de aviso de tipo info, error o atención
def aviso(titulo, texto, tipo="info"):
    clase = {"info": "aviso", "error": "aviso aviso--error", "atencion": "aviso aviso--atencion"}[tipo]
    st.html(f"""
    <div class="{clase}">
        <div>
            <p class="aviso__titulo">{html.escape(titulo)}</p>
            <p class="aviso__texto">{html.escape(texto)}</p>
        </div>
    </div>
    """)


# Título de un bloque de la barra lateral
def titulo_lateral(titulo, nota=""):
    detalle = f'<p class="lateral__nota">{html.escape(nota)}</p>' if nota else ""
    st.html(f'<p class="lateral__titulo">{html.escape(titulo)}</p>{detalle}')


# Aplica la plantilla y pinta un gráfico de Plotly
def grafico(figura, titulo):
    figura.update_layout(template="sneaker", title=titulo, separators=",.")
    st.plotly_chart(figura, width="stretch", config={"displaylogo": False})



# Aviso de Laboratorio sintético
def laboratorio(texto):
    st.html(f"""
    <div class="laboratorio">
        <span class="laboratorio__etiqueta">Laboratorio sintético</span>
        <p class="laboratorio__texto">{html.escape(texto)}</p>
    </div>
    """)


# Lista de limitaciones
def lista_limitaciones(frases):
    elementos = "".join(f'<li class="lista-limitaciones__elemento">{html.escape(f)}</li>' for f in frases)
    st.html(f'<ul class="lista-limitaciones">{elementos}</ul>')


# Mapa de calor con la escala naranja del panel
def mapa_calor(tabla, titulo, etiqueta_x, etiqueta_color, formato="%{z:.1f} %"):
    figura = go.Figure(go.Heatmap(
        z=tabla.to_numpy(), x=list(tabla.columns), y=list(tabla.index),
        colorscale=[[0, COLORES["superficie"]], [0.5, "rgb(150, 95, 0)"], [1, COLORES["naranja"]]],
        colorbar={"title": etiqueta_color}, hovertemplate=f"%{{y}} · %{{x}}<br>{formato}<extra></extra>",
        xgap=2, ygap=2,
    ))
    figura.update_xaxes(title=etiqueta_x, type="category", showgrid=False)
    figura.update_yaxes(type="category", showgrid=False, autorange="reversed")
    figura.update_layout(template="sneaker", title=titulo, separators=",.", height=max(320, 32 * len(tabla) + 120))
    st.plotly_chart(figura, width="stretch", config={"displaylogo": False})