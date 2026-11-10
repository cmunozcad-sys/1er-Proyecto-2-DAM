import pytest

import analiticas
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