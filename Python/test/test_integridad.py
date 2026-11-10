import pandas as pd

import pipeline
from tests.conftest import escribir, leer


def ejecutar(carpeta):
    tablas, manifiesto, registro = pipeline.cargar_datos(carpeta, "PRUEBA")
    validas, resumen = pipeline.validar_datos(tablas, registro)
    return validas, registro.a_dataframe()


def test_id_huerfano(carpeta):
    pedidos = leer(carpeta, "pedidos")
    pedidos.loc[1, "id_cliente"] = "99"
    escribir(carpeta, "pedidos", pedidos)

    validas, incidencias = ejecutar(carpeta)
    huerfano = incidencias[(incidencias["tabla"] == "pedidos") & (incidencias["regla"] == "03")]

    assert huerfano["gravedad"].tolist() == ["BLOQUEANTE"]
    assert "2" not in validas["pedidos"]["id_pedido"].tolist()
    assert "3" not in validas["lineas"]["id_linea"].tolist()


def test_id_duplicado(carpeta):
    pedidos = leer(carpeta, "pedidos")
    copia = pedidos.iloc[[0]].assign(estado="BORRADOR")
    escribir(carpeta, "pedidos", pd.concat([pedidos, copia]))

    validas, incidencias = ejecutar(carpeta)

    assert (incidencias["regla"] == "02").sum() == 2
    assert "1" not in validas["pedidos"]["id_pedido"].tolist()


def test_cantidad_negativa(carpeta):
    lineas = leer(carpeta, "lineas")
    lineas.loc[0, "cantidad"] = "-2"
    escribir(carpeta, "lineas", lineas)

    validas, incidencias = ejecutar(carpeta)

    assert incidencias.iloc[0]["regla"] == "05"
    assert len(validas["lineas"]) == 2


def test_cardinalidad_del_merge(carpeta):
    tablas, manifiesto, registro = pipeline.cargar_datos(carpeta, "PRUEBA")
    validas, resumen = pipeline.validar_datos(tablas, registro)
    validas["modelos"] = pd.concat([validas["modelos"], validas["modelos"].iloc[[0]]])

    lineas, pedidos = pipeline.integrar_datos(validas, registro)

    assert lineas is None
    assert registro.hay_bloqueantes()


def test_pedido_multilinea_cuenta_una_vez(carpeta):
    tablas, manifiesto, registro = pipeline.cargar_datos(carpeta, "PRUEBA")
    validas, resumen = pipeline.validar_datos(tablas, registro)
    lineas, pedidos = pipeline.integrar_datos(validas, registro)

    pedido = pedidos.set_index("id_pedido").loc["1"]
    assert len(lineas) == 3
    assert len(pedidos) == 2
    assert pedido["num_lineas"] == 2
    assert pedido["pares"] == 5
    assert pedido["importe"] == 350.00


def test_csv_original_no_se_modifica(carpeta):
    pedidos = leer(carpeta, "pedidos")
    pedidos.loc[0, "id_cliente"] = "99"
    escribir(carpeta, "pedidos", pedidos)
    antes = (carpeta / "pedidos.csv").read_bytes()

    ejecutar(carpeta)

    assert (carpeta / "pedidos.csv").read_bytes() == antes