import pandas as pd
import pytest

import analiticas
import config
import pipeline

@pytest.fixture
def datos(carpeta):
    tablas, manifiesto, registro = pipeline.cargar_datos(carpeta, "PRUEBA")
    validas, resumen = pipeline.validar_datos(tablas, registro)
    lineas, pedidos = pipeline.integrar_datos(validas, registro)
    return analiticas.aplicar_filtros(analiticas.preparar_datos(validas, lineas, pedidos, "PRUEBA"))


def kpi(datos, nombre):
    kpis = analiticas.calcular_kpis(datos).set_index("kpi")["valor"]
    return kpis[nombre]


def test_cancelados_fuera_de_ventas_pero_en_actividad(datos):
    assert kpi(datos, "pedidos_totales") == 2
    assert kpi(datos, "pedidos_cancelados") == 1
    assert kpi(datos, "ingresos_validos") == 350.00
    assert kpi(datos, "pares_vendidos") == 5


def test_ticket_divide_entre_pedidos_y_no_entre_lineas(datos):
    assert kpi(datos, "ticket_medio") == 350.00
    assert kpi(datos, "pares_por_pedido") == 5
    assert kpi(datos, "precio_medio_par") == 70.00


def test_filtro_no_aplicado_no_restringe(datos):
    filtrados = analiticas.aplicar_filtros(datos, {"modelos": [], "tallas": [], "fecha_desde": None})
    assert len(filtrados["pedidos"]) == len(datos["pedidos"])
    assert len(filtrados["lineas"]) == len(datos["lineas"])


def test_filtro_por_talla_recalcula_el_pedido(datos):
    filtrados = analiticas.aplicar_filtros(datos, {"tallas": [41.0]})
    pedido = filtrados["pedidos"].set_index("id_pedido").loc["1"]
    assert pedido["pares"] == 3
    assert pedido["importe"] == 210.00
    assert kpi(filtrados, "ingresos_validos") == 210.00


def test_kpis_y_ventas_mensuales_cuadran(datos):
    mensual = analiticas.ventas_por_periodo(datos)
    assert mensual["ingresos"].sum() == kpi(datos, "ingresos_validos")
    assert mensual["pedidos"].sum() == kpi(datos, "pedidos_confirmados")


def test_clasificacion_abc(datos):
    abc = analiticas.modelos_abc(datos).set_index("modelo")
    assert abc.loc["Cometa", "clase_abc"] == "A"
    assert abc.loc["Titan", "ingresos"] == 0
    assert abc["acumulado_pct"].iloc[-1] == 100



def test_rfm_empates_reciben_la_misma_puntuacion(datos):
    rfm = analiticas.clientes_rfm(datos)
    assert len(rfm) == 1
    assert rfm.loc[0, "frequency"] == 1
    assert rfm.loc[0, "monetary"] == 350.00
    puntos = analiticas.puntuar(pd.Series([1, 1, 1, 5]))
    assert puntos.iloc[0] == puntos.iloc[1] == puntos.iloc[2]


def test_cobertura_sin_demanda_es_nd(datos):
    stock = analiticas.stock_cobertura(datos).set_index(["id_variante", "talla"])
    fila = stock.loc[("2", 42.0)]
    assert fila["demanda_reciente"] == 0
    assert fila["cobertura_texto"] == "N/D"
    assert fila["alerta"] == "BAJO MÍNIMO"


def test_anomalias_no_eliminan_registros(datos):
    antes = len(datos["pedidos"])
    resultado = analiticas.anomalias(datos)
    assert len(datos["pedidos"]) == antes
    assert (resultado["decision"] == "Se conserva y se marca").all()


def test_margen_no_calculable_sin_coste(datos):
    margen = analiticas.margen(datos)
    assert margen["margen"].isna().all()
    assert margen["estado"].str.startswith("NO CALCULABLE").all()


def test_reconciliacion_detecta_diferencias(datos, carpeta):
    referencia = pd.DataFrame({"indicador": ["pedidos_totales", "ingresos_validos"], "valor_sql": [2, 999.99]})
    referencia.to_csv(carpeta / config.FICHERO_REFERENCIA_SQL, index=False)

    estados = analiticas.reconciliacion_sql(datos, carpeta).set_index("indicador")["estado"]
    assert estados["pedidos_totales"] == "OK"
    assert estados["ingresos_validos"] == "DIFERENCIA"
    assert estados["lineas_totales"] == "SIN REFERENCIA"