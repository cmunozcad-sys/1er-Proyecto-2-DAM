import generador_datos


def test_misma_semilla_mismos_datos():
    primera = generador_datos.generar(42)
    segunda = generador_datos.generar(42)
    for tabla in primera:
        assert primera[tabla].equals(segunda[tabla])


def test_distinta_semilla_distintos_datos():
    assert not generador_datos.generar(42)["pedidos"].equals(generador_datos.generar(7)["pedidos"])


def test_sintetico_cumple_los_minimos():
    tablas = generador_datos.generar(42)
    meses = tablas["pedidos"]["fecha_pedido"].dt.to_period("M").nunique()
    assert len(tablas["pedidos"]) >= 800
    assert len(tablas["lineas"]) >= 1600
    assert len(tablas["clientes"]) >= 40
    assert len(tablas["modelos"]) >= 12
    assert meses >= 18