import pytest

import analiticas
import config
import generador_datos
import pipeline


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


def test_matriz_modelo_mes_cuenta_los_pares_vendidos(carpeta):
    df = analiticas.matriz_modelo_mes(preparar(carpeta, "PRUEBA")).set_index("modelo")
    assert df.loc["Cometa", "2026-10"] == 5
    assert "Titan" not in df.index


def test_pocos_meses_no_se_calcula_estacionalidad_ni_mezcla(carpeta):
    datos = preparar(carpeta, "PRUEBA")
    assert analiticas.productos_estacionales(datos).attrs["estado"].startswith("NO CALCULABLE")
    assert analiticas.cambios_mezcla_tallas(datos).attrs["estado"].startswith("NO CALCULABLE")


def test_matriz_modelo_mes_suma_lo_mismo_que_la_demanda(sintetico):
    matriz = analiticas.matriz_modelo_mes(sintetico)
    demanda = analiticas.demanda_modelo_mes(sintetico)
    assert matriz.drop(columns="modelo").to_numpy().sum() == demanda["unidades_modelo_mes"].sum()


def test_indices_estacionales_tienen_media_uno(sintetico):
    df = analiticas.productos_estacionales(sintetico)
    assert df.attrs["estado"].startswith("CALCULADO")
    assert df[analiticas.MESES_DEL_ANIO].mean(axis=1).round(1).eq(1.0).all()
    assert (df["es_estacional"] == (df["indice_pico"] >= config.UMBRAL_ESTACIONALIDAD)).all()


def test_mezcla_de_tallas_suma_cien_en_cada_periodo(sintetico):
    df = analiticas.cambios_mezcla_tallas(sintetico)
    assert df.attrs["estado"].startswith("CALCULADO")
    assert df["pct_anterior"].sum() == pytest.approx(100, abs=0.5)
    assert df["pct_reciente"].sum() == pytest.approx(100, abs=0.5)
    assert set(df["cambio"]) <= {"SUBE", "BAJA", "ESTABLE"}
