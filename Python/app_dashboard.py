import streamlit as st

import analiticas
import config
import refresco
from dashboard import interfaz, vistas
from utils.trazas import con_linaje

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


@st.cache_data(show_spinner="Entrenando el modelo de predicción…")
def predecir_sintetico(origen, huella_ficheros, _datos):
    return prediccion.evaluar_prediccion(_datos)


def predecir(ciclo):
    if ciclo["origen"] == "REAL":
        return prediccion.evaluar_prediccion(ciclo["datos"])
    return predecir_sintetico(ciclo["origen"], ciclo["huella"], ciclo["datos"])


def clave(filtro):
    return f"filtro_{filtro}_{st.session_state.get('origen', '')}"


def restablecer_filtros():
    for filtro in FILTROS + ["periodo_elegido"]:
        st.session_state.pop(clave(filtro), None)


def marcar_periodo():
    st.session_state[clave("periodo_elegido")] = True


def actualizar_ahora():
    st.session_state["actualizar_ahora"] = True


def filtros_guardados():
    filtros = {filtro: st.session_state.get(clave(filtro), []) for filtro in FILTROS if filtro != "periodo"}
    periodo = st.session_state.get(clave("periodo"), ())
    if st.session_state.get(clave("periodo_elegido")) and len(periodo) == 2:
        filtros["fecha_desde"], filtros["fecha_hasta"] = periodo
    return filtros


def filtros_laterales(datos):
    pedidos, lineas = datos["pedidos"], datos["lineas"]
    nombres_modelo = datos["modelos"].set_index("id_modelo")["nombre"]
    nombres_cliente = datos["clientes"].set_index("id_cliente")["ref_odoo"]
    primera, ultima = pedidos["fecha_pedido"].min().date(), pedidos["fecha_pedido"].max().date()

    interfaz.titulo_lateral("Filtros", "Se aplican a todas las vistas. Vacío = sin restricción.")
    st.date_input("Periodo del pedido", value=(primera, ultima), min_value=primera, max_value=ultima,
                  format="DD/MM/YYYY", key=clave("periodo"), on_change=marcar_periodo)
    st.multiselect("Modelo", sorted(lineas["id_modelo"].unique(), key=lambda i: nombres_modelo[i]),
                   format_func=lambda i: nombres_modelo[i], placeholder="Todos", key=clave("modelos"))
    st.multiselect("Talla", sorted(lineas["talla"].unique()), format_func=lambda t: f"{t:g}", placeholder="Todas",
                   key=clave("tallas"))
    st.multiselect("Tipo de pedido", config.TIPOS_PEDIDO, placeholder="Todos", key=clave("tipos"))
    st.multiselect("Estado", config.ESTADOS_PEDIDO, placeholder="Todos", key=clave("estados"))
    st.multiselect("Cliente", sorted(pedidos["id_cliente"].unique(), key=lambda c: nombres_cliente[c]),
                   format_func=lambda c: nombres_cliente[c], placeholder="Todos", key=clave("clientes"))
    st.button("Restablecer filtros", on_click=restablecer_filtros, width="stretch")


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
        st.download_button(nombre, con_linaje(tabla).to_csv(index=False).encode("utf-8"), file_name=fichero,
                           mime="text/csv", width="stretch", key=f"descarga_{nombre}")


def ejecutar_refresco(carpeta, origen):
    anterior = st.session_state.get(f"refresco_{origen}", {})
    ultimo = anterior.get("ultimo")
    ciclo = refresco.ejecutar_ciclo(carpeta, origen, ultimo["huella"] if ultimo else None)
    estado = {"ultimo": ciclo, "valido": refresco.publicar(ciclo, anterior.get("valido"))}
    st.session_state[f"refresco_{origen}"] = estado
    return estado


def pintar(estado, carpeta, origen):
    ultimo, valido = estado["ultimo"], estado["valido"]
    if valido:
        interfaz.cabecera(origen, valido["datos"]["fecha_corte"], valido["comprobado"])
    vistas.barra_refresco(ultimo, valido)
    if ultimo is not valido:
        vistas.ciclo_fallido(ultimo, valido)
    if not valido:
        return

    datos = valido["datos"]
    vista = st.segmented_control("Vista", VISTAS, default=VISTAS[0], key="vista", label_visibility="collapsed")
    filtros = filtros_guardados()
    filtrados = analiticas.aplicar_filtros(datos, filtros)
    if filtrados["pedidos"].empty:
        interfaz.aviso("Sin resultados", "Ningún pedido cumple los filtros elegidos. Prueba a quitar alguno.",
                       "atencion")
        return

    if vista == VISTAS[1]:
        vistas.producto(filtrados)
    elif vista == VISTAS[2]:
        vistas.clientes(datos, filtrados)
    elif vista == VISTAS[3]:
        vistas.almacen(datos, filtrados)
    elif vista == VISTAS[4]:
        vistas.calidad(valido, datos, carpeta)
    elif vista == VISTAS[5]:
        vistas.prediccion(predecir(valido) if prediccion else None, origen)
    else:
        vistas.direccion(datos, filtrados, filtros)


@st.fragment(run_every=config.INTERVALO_REFRESCO)
def panel(carpeta, origen):
    completa = st.session_state.pop("ejecucion_completa", False)
    pedido = st.session_state.pop("actualizar_ahora", False)
    estado = st.session_state.get(f"refresco_{origen}")
    if pedido or refresco.toca_ciclo(estado["ultimo"]["comprobado"] if estado else None):
        estado = ejecutar_refresco(carpeta, origen)
        if not completa and estado["valido"] is estado["ultimo"]:
            st.rerun()
    pintar(estado, carpeta, origen)


def main():
    interfaz.cargar_estilos()

    with st.sidebar:
        interfaz.titulo_lateral("Origen de los datos")
        eleccion = st.radio("Origen de los datos", list(ORIGENES), key="origen", label_visibility="collapsed")
        st.button("Actualizar ahora", on_click=actualizar_ahora, width="stretch")
    carpeta, origen = ORIGENES[eleccion]

    st.session_state["ejecucion_completa"] = True
    panel(carpeta, origen)

    valido = st.session_state[f"refresco_{origen}"]["valido"]
    if not valido:
        return
    with st.sidebar:
        filtros_laterales(valido["datos"])
        filtrados = analiticas.aplicar_filtros(valido["datos"], filtros_guardados())
        if not filtrados["pedidos"].empty:
            descargas(filtrados, origen)


main()
