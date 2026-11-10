import main
from tests.conftest import escribir, leer


def test_ejecucion_completa_guarda_resultados(carpeta, tmp_path):
    salida = tmp_path / "salida"

    assert main.ejecutar(carpeta, "PRUEBA", salida)
    assert (salida / "csv" / "kpis.csv").exists()
    assert (salida / "csv" / "indice_resultados.csv").exists()
    assert len(list((salida / "figuras").glob("*.png"))) == 8


def test_bloqueante_no_publica_resultados(carpeta, tmp_path):
    pedidos = leer(carpeta, "pedidos")
    pedidos.loc[0, "id_cliente"] = "99"
    escribir(carpeta, "pedidos", pedidos)
    salida = tmp_path / "salida"

    assert not main.ejecutar(carpeta, "PRUEBA", salida)
    assert (salida / "csv" / "incidencias.csv").exists()
    assert not (salida / "csv" / "kpis.csv").exists()
    assert not (salida / "figuras").exists()