import analiticas
import config
import generador_datos
import pipeline


def preparar(carpeta, origen):
    tablas, manifiesto, registro = pipeline.cargar_datos(carpeta, origen)
    validas, resumen = pipeline.validar_datos(tablas, registro)
    lineas, pedidos = pipeline.integrar_datos(validas, registro)
    return analiticas.aplicar_filtros(analiticas.preparar_datos(validas, lineas, pedidos, origen))


def test_pocos_clientes_no_se_agrupan(carpeta):
    resultado = analiticas.clustering_clientes(preparar(carpeta, "PRUEBA"))
    assert resultado["estado"].startswith("NO CALCULABLE")
    assert resultado["perfil"].empty


def test_clustering_con_historico_sintetico(tmp_path):
    generador_datos.guardar(generador_datos.generar(config.SEMILLA), tmp_path)
    resultado = analiticas.clustering_clientes(preparar(tmp_path, "SINTETICO"))

    evaluacion = resultado["evaluacion"]
    assert evaluacion["k"].tolist() == config.VALORES_K
    assert evaluacion["elegido"].sum() == 1
    assert resultado["perfil"]["clientes"].sum() == len(resultado["asignacion"])
    assert resultado["perfil"]["nombre_cluster"].is_unique
    assert resultado["perfil"]["peso_clientes_pct"].sum().round() == 100