from datetime import datetime
from pathlib import Path

import streamlit as st

import analiticas
import config
import pipeline
from dashboard import interfaz, vistas

try:
    import prediccion
except ImportError:
    prediccion = None

st.set_page_config(page_title="Sneaker Factory · Panel de datos", page_icon=str(interfaz.RECURSOS / "logo.png"),
                   layout="wide")

ORIGENES = {
    "Datos reales": (config.ENTRADA_REAL, "REAL"),
    "Histórico sintético": (config.ENTRADA_SINTETICA, "SINTETICO"),
}
VISTAS = ["01 · Dirección", "02 · Producto y ventas", "03 · Clientes", "04 · Almacén", "05 · Calidad y auditoría",
          "06 · Modelos predictivos"]
FILTROS = ["periodo", "modelos", "tallas", "tipos", "estados", "clientes"]


def huella(carpeta):
    return tuple((f.name, f.stat().st_mtime_ns, f.stat().st_size) for f in sorted(Path(carpeta).glob("*.csv")))


@st.cache_data(show_spinner="Cargando y validando los datos…")
def cargar(carpeta, origen, huella_ficheros):
    tablas, manifiesto, registro = pipeline.cargar_datos(carpeta, origen)
    validas, resumen = pipeline.validar_datos(tablas, registro)
    lineas, pedidos = pipeline.integrar_datos(validas, registro)
    bloqueado = registro.hay_bloqueantes() or pedidos is None
    return {
        "datos": None if bloqueado else analiticas.preparar_datos(validas, lineas, pedidos, origen),
        "resumen": resumen,
        "incidencias": registro.a_dataframe(),
        "manifiesto": manifiesto,
        "bloqueado": bloqueado,
        "cargado": datetime.now(),
    }


@st.cache_data(show_spinner="Entrenando el modelo de predicción…")
def predecir(carpeta, origen, huella_ficheros):
    datos = cargar(carpeta, origen, huella_ficheros)["datos"]
    return prediccion.evaluar_prediccion(datos)


def clave(filtro):
    return f"filtro_{filtro}_{st.session_state.get('origen', '')}"


def restablecer_filtros():
    for filtro in FILTROS:
        st.session_state.pop(clave(filtro), None)


def filtros_laterales(datos):
    pedidos, lineas = datos["pedidos"], datos["lineas"]
    nombres_modelo = datos["modelos"].set_index("id_modelo")["nombre"]
    nombres_cliente = datos["clientes"].set_index("id_cliente")["ref_odoo"]
    primera, ultima = pedidos["fecha_pedido"].min().date(), pedidos["fecha_pedido"].max().date()

    interfaz.titulo_lateral("Filtros", "Se aplican a todas las vistas. Vacío = sin restricción.")
    periodo = st.date_input("Periodo del pedido", value=(primera, ultima), min_value=primera, max_value=ultima,
                            format="DD/MM/YYYY", key=clave("periodo"))
    modelos = st.multiselect("Modelo", sorted(lineas["id_modelo"].unique(), key=lambda i: nombres_modelo[i]),
                             format_func=lambda i: nombres_modelo[i], placeholder="Todos",
                             key=clave("modelos"))
    tallas = st.multiselect("Talla", sorted(lineas["talla"].unique()), format_func=lambda t: f"{t:g}",
                            placeholder="Todas", key=clave("tallas"))
    tipos = st.multiselect("Tipo de pedido", config.TIPOS_PEDIDO, placeholder="Todos", key=clave("tipos"))
    estados = st.multiselect("Estado", config.ESTADOS_PEDIDO, placeholder="Todos", key=clave("estados"))
    clientes = st.multiselect("Cliente", sorted(pedidos["id_cliente"].unique(), key=lambda c: nombres_cliente[c]),
                              format_func=lambda c: nombres_cliente[c], placeholder="Todos",
                              key=clave("clientes"))
    st.button("Restablecer filtros", on_click=restablecer_filtros, width="stretch")

    filtros = {"modelos": modelos, "tallas": tallas, "tipos": tipos, "estados": estados, "clientes": clientes}
    if len(periodo) == 2 and periodo != (primera, ultima):
        filtros["fecha_desde"], filtros["fecha_hasta"] = periodo
    return filtros


def descargas(filtrados, origen):
    interfaz.titulo_lateral("Descargas", "CSV con los filtros aplicados.")
    tablas = {
        "Pedidos": analiticas.pedidos_unicos(filtrados),
        "Ventas por mes": analiticas.ventas_por_periodo(filtrados),
        "Modelos ABC": analiticas.modelos_abc(filtrados),
        "Clientes RFM": analiticas.clientes_rfm(filtrados),
        "Stock y cobertura": analiticas.stock_cobertura(filtrados),
    }
    for nombre, tabla in tablas.items():
        fichero = f"{tabla.attrs.get('nombre', nombre)}_{origen.lower()}.csv"
        st.download_button(nombre, tabla.to_csv(index=False).encode("utf-8"), file_name=fichero, mime="text/csv",
                           width="stretch", key=f"descarga_{nombre}")


def main():
    interfaz.cargar_estilos()

    with st.sidebar:
        interfaz.titulo_lateral("Origen de los datos")
        eleccion = st.radio("Origen de los datos", list(ORIGENES), key="origen", label_visibility="collapsed")
    carpeta, origen = ORIGENES[eleccion]
    huella_ficheros = huella(carpeta)
    carga = cargar(carpeta, origen, huella_ficheros)

    if carga["bloqueado"]:
        interfaz.aviso("No se publican resultados",
                       "Los CSV tienen incidencias bloqueantes (fichero que falta, columna ausente o clave huérfana). "
                       "Revisa la tabla de incidencias.", "error")
        st.dataframe(carga["incidencias"], width="stretch", hide_index=True)
        return

    datos = carga["datos"]
    interfaz.cabecera(origen, datos["fecha_corte"], carga["cargado"])
    with st.sidebar:
        filtros = filtros_laterales(datos)

    vista = st.segmented_control("Vista", VISTAS, default=VISTAS[0], key="vista", label_visibility="collapsed")
    filtrados = analiticas.aplicar_filtros(datos, filtros)
    if filtrados["pedidos"].empty:
        interfaz.aviso("Sin resultados", "Ningún pedido cumple los filtros elegidos. Prueba a quitar alguno.",
                       "atencion")
        return

    with st.sidebar:
        descargas(filtrados, origen)

    if vista == VISTAS[1]:
        vistas.producto(filtrados)
    elif vista == VISTAS[2]:
        vistas.clientes(datos, filtrados)
    elif vista == VISTAS[3]:
        vistas.almacen(datos, filtrados)
    elif vista == VISTAS[4]:
        vistas.calidad(carga, datos, carpeta)
    elif vista == VISTAS[5]:
        resultado = predecir(carpeta, origen, huella_ficheros) if prediccion else None
        vistas.prediccion(resultado, origen)
    else:
        vistas.direccion(datos, filtrados, filtros)


main()
