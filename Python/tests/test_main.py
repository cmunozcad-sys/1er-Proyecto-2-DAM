import pandas as pd
import pytest

import main
from tests.conftest import escribir, leer


def kpis(salida):
    return pd.read_csv(salida / "csv" / "kpis.csv").set_index("kpi")["valor"]


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


@pytest.mark.parametrize("argumentos", [["--modelo", "1"], ["--cliente", "1"]])
def test_filtros_de_identificador_desde_consola(carpeta, tmp_path, argumentos):
    filtros = main.filtros_de(main.leer_argumentos(argumentos))
    salida = tmp_path / "salida"

    assert main.ejecutar(carpeta, "PRUEBA", salida, figuras=False, filtros=filtros)
    assert kpis(salida)["pares_vendidos"] == 5
    assert kpis(salida)["ingresos_validos"] == 350.00


def test_filtro_sin_pedidos_avisa_y_no_publica(carpeta, tmp_path, capsys):
    filtros = main.filtros_de(main.leer_argumentos(["--desde", "2030-01-01"]))
    salida = tmp_path / "salida"

    assert not main.ejecutar(carpeta, "PRUEBA", salida, figuras=False, filtros=filtros)
    assert "Ningún pedido cumple los filtros" in capsys.readouterr().out
    assert not (salida / "csv" / "kpis.csv").exists()


def test_fecha_mal_escrita_da_error_claro(capsys):
    with pytest.raises(SystemExit) as salida:
        main.leer_argumentos(["--desde", "hola"])

    assert salida.value.code == 2
    assert "fecha no válida: 'hola' (formato AAAA-MM-DD)" in capsys.readouterr().err