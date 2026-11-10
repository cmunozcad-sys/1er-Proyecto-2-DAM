import analiticas
import pipeline
import visualizaciones


def test_se_generan_las_ocho_figuras(carpeta, tmp_path):
    tablas, manifiesto, registro = pipeline.cargar_datos(carpeta, "PRUEBA")
    validas, resumen = pipeline.validar_datos(tablas, registro)
    lineas, pedidos = pipeline.integrar_datos(validas, registro)
    datos = analiticas.aplicar_filtros(analiticas.preparar_datos(validas, lineas, pedidos, "PRUEBA"))

    salida = tmp_path / "figuras"
    lecturas = visualizaciones.guardar_figuras(datos, salida)

    assert len(list(salida.glob("*.png"))) == 8
    assert lecturas["lectura"].str.len().gt(0).all()