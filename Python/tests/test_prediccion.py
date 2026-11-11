import pytest

import analiticas
import config
import generador_datos
import pipeline
import prediccion


def preparar(carpeta, origen):
    tablas, manifiesto, registro = pipeline.cargar_datos(carpeta, origen)
    validas, resumen = pipeline.validar_datos(tablas, registro)
    lineas, pedidos = pipeline.integrar_datos(validas, registro)
    return analiticas.aplicar_filtros(analiticas.preparar_datos(validas, lineas, pedidos, origen))


@pytest.fixture(scope="module")
def sintetico(tmp_path_factory):
    carpeta = tmp_path_factory.mktemp("sintetico")
    generador_datos.guardar(generador_datos.generar(config.SEMILLA), carpeta)
    return preparar(carpeta, "SINTETICO")


def test_pocos_meses_no_se_predice(carpeta):
    resultado = prediccion.evaluar_prediccion(preparar(carpeta, "PRUEBA"))
    assert resultado["estado"].startswith("NO CALCULABLE")
    assert resultado["metricas"].empty


def test_separacion_temporal_sin_mezclar_fechas(sintetico):
    entrenamiento, prueba = prediccion.separar_por_fecha(prediccion.construir_dataset(sintetico))
    assert prueba["mes"].nunique() == config.MESES_PRUEBA
    assert entrenamiento["mes"].max() < prueba["mes"].min()


def test_predictores_no_usan_el_mes_objetivo(sintetico):
    original = prediccion.construir_dataset(sintetico)
    ultimo = original["mes"].max()

    alterado = dict(sintetico)
    lineas = sintetico["lineas"].copy()
    lineas.loc[lineas["periodo"] == ultimo, "cantidad"] *= 10
    alterado["lineas"] = lineas
    cambiado = prediccion.construir_dataset(alterado)

    columnas = prediccion.PREDICTORES_NUMERICOS
    antes = original[original["mes"] == ultimo][columnas].reset_index(drop=True)
    despues = cambiado[cambiado["mes"] == ultimo][columnas].reset_index(drop=True)
    assert antes.equals(despues)


def test_baseline_repite_el_mes_anterior(sintetico):
    detalle = prediccion.evaluar_prediccion(sintetico)["detalle"]
    dataset = prediccion.construir_dataset(sintetico).set_index(["mes", "id_modelo"])
    for _, fila in detalle.head(5).iterrows():
        assert fila["baseline"] == dataset.loc[(fila["mes"], fila["id_modelo"]), "demanda_mes_anterior"]


def test_resultado_cumple_el_acuerdo_con_el_dashboard(sintetico):
    resultado = prediccion.evaluar_prediccion(sintetico)
    assert resultado["estado"].startswith("CALCULADO")
    assert {"modelo", "mae", "rmse"} <= set(resultado["metricas"].columns)
    assert {"id_modelo", "modelo", "mae_baseline", "mae_modelo"} <= set(resultado["por_modelo"].columns)
    assert {"mes", "real", "baseline", "prediccion"} <= set(resultado["serie"].columns)
    assert resultado["metricas"]["modelo"].tolist() == ["baseline", "RandomForestRegressor"]
