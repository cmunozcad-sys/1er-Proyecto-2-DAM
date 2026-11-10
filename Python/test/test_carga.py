import pipeline
from tests.conftest import escribir, leer


def reglas(registro):
    return registro.a_dataframe()


def test_datos_correctos_sin_incidencias(carpeta):
    tablas, manifiesto, registro = pipeline.cargar_datos(carpeta, "PRUEBA")
    validas, resumen = pipeline.validar_datos(tablas, registro)

    assert len(tablas) == 5
    assert registro.incidencias == []
    assert (resumen["porcentaje_calidad"] == 100).all()
    assert manifiesto["filas"].tolist() == [2, 2, 2, 3, 3]


def test_ruta_inexistente(tmp_path):
    tablas, manifiesto, registro = pipeline.cargar_datos(tmp_path / "no_existe", "PRUEBA")

    assert tablas == {}
    assert registro.hay_bloqueantes()
    assert (reglas(registro)["regla"] == "01").sum() == 5


def test_csv_vacio(carpeta):
    (carpeta / "clientes.csv").write_text("", encoding="utf-8")
    tablas, manifiesto, registro = pipeline.cargar_datos(carpeta, "PRUEBA")

    assert "clientes" not in tablas
    incidencia = reglas(registro).iloc[0]
    assert incidencia["regla"] == "01"
    assert incidencia["gravedad"] == "BLOQUEANTE"


def test_columna_ausente(carpeta):
    escribir(carpeta, "lineas", leer(carpeta, "lineas").drop(columns="talla"))
    tablas, manifiesto, registro = pipeline.cargar_datos(carpeta, "PRUEBA")

    assert "lineas" not in tablas
    assert "talla" in reglas(registro).iloc[0]["descripcion"]


def test_fecha_corrupta(carpeta):
    pedidos = leer(carpeta, "pedidos")
    pedidos.loc[0, "fecha_pedido"] = "2026-13-45"
    escribir(carpeta, "pedidos", pedidos)

    tablas, manifiesto, registro = pipeline.cargar_datos(carpeta, "PRUEBA")
    validas, resumen = pipeline.validar_datos(tablas, registro)

    assert set(reglas(registro)["regla"]) >= {"CONV", "04"}
    assert "1" not in validas["pedidos"]["id_pedido"].tolist()