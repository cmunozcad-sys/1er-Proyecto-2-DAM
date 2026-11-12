from datetime import datetime, timedelta

import pandas as pd

import analiticas
import config
import refresco
from tests.conftest import escribir, leer
from utils.trazas import con_linaje


def kpis(ciclo):
    return analiticas.calcular_kpis(ciclo["datos"]).set_index("kpi")["valor"]


def test_sin_cambios_da_los_mismos_kpis(carpeta):
    primero = refresco.ejecutar_ciclo(carpeta, "PRUEBA")
    segundo = refresco.ejecutar_ciclo(carpeta, "PRUEBA", primero["huella"])

    assert primero["estado"] == refresco.CORRECTO
    assert segundo["estado"] == refresco.SIN_CAMBIOS
    assert segundo["comprobado"] > primero["comprobado"]
    pd.testing.assert_series_equal(kpis(primero), kpis(segundo))


def test_columna_clave_ausente_no_publica(carpeta):
    valido = refresco.ejecutar_ciclo(carpeta, "PRUEBA")
    escribir(carpeta, "pedidos", leer(carpeta, "pedidos").drop(columns="id_cliente"))

    ciclo = refresco.ejecutar_ciclo(carpeta, "PRUEBA", valido["huella"])

    assert ciclo["estado"] == refresco.DATOS_INVALIDOS
    assert ciclo["datos"] is None
    assert "id_cliente" in ciclo["explicacion"]
    assert refresco.publicar(ciclo, valido) is valido


def test_se_recupera_solo_cuando_el_csv_vuelve_a_estar_bien(carpeta):
    original = leer(carpeta, "pedidos")
    escribir(carpeta, "pedidos", original.drop(columns="id_cliente"))
    fallido = refresco.ejecutar_ciclo(carpeta, "PRUEBA")

    escribir(carpeta, "pedidos", original)
    recuperado = refresco.ejecutar_ciclo(carpeta, "PRUEBA", fallido["huella"])

    assert recuperado["estado"] == refresco.CORRECTO
    assert refresco.publicar(recuperado, None) is recuperado


def test_fichero_ausente_es_error_de_carga(carpeta):
    (carpeta / config.FICHEROS["stock"]).unlink()

    ciclo = refresco.ejecutar_ciclo(carpeta, "PRUEBA")

    assert ciclo["estado"] == refresco.ERROR_CARGA
    assert ciclo["datos"] is None
    assert config.FICHEROS["stock"] in ciclo["explicacion"]


def test_pedido_nuevo_con_dos_lineas_suma_una_sola_vez(carpeta):
    antes = refresco.ejecutar_ciclo(carpeta, "PRUEBA")

    pedido = {"id_pedido": "3", "ref_odoo": "PED-0002", "tipo": "ESTANDAR", "estado": "CONFIRMADO",
              "fecha_pedido": "2026-10-10 11:00:00", "fecha_entrega_prevista": "2026-10-25",
              "fecha_confirmacion": "2026-10-10 12:00:00", "fecha_cancelacion": "NULL", "total": "230.00",
              "id_cliente": "2"}
    lineas = [
        {"id_linea": "4", "id_pedido": "3", "id_variante": "1", "id_modelo": "1", "color": "negro", "talla": "40.0",
         "cantidad": "2", "precio_unitario": "70.00", "logo_club": "False", "personalizada": "False"},
        {"id_linea": "5", "id_pedido": "3", "id_variante": "2", "id_modelo": "2", "color": "blanco", "talla": "42.0",
         "cantidad": "1", "precio_unitario": "90.00", "logo_club": "False", "personalizada": "False"},
    ]
    escribir(carpeta, "pedidos", pd.concat([leer(carpeta, "pedidos"), pd.DataFrame([pedido])]))
    escribir(carpeta, "lineas", pd.concat([leer(carpeta, "lineas"), pd.DataFrame(lineas)]))

    despues = refresco.ejecutar_ciclo(carpeta, "PRUEBA", antes["huella"])
    previo, nuevo = kpis(antes), kpis(despues)

    assert despues["estado"] == refresco.CORRECTO
    assert nuevo["pedidos_totales"] == previo["pedidos_totales"] + 1
    assert nuevo["pedidos_confirmados"] == previo["pedidos_confirmados"] + 1
    assert nuevo["pares_vendidos"] == previo["pares_vendidos"] + 3
    assert nuevo["ingresos_validos"] == round(previo["ingresos_validos"] + 230.00, 2)


def test_solo_toca_ciclo_al_cumplirse_el_intervalo():
    ultima = datetime(2026, 11, 12, 10, 0, 0)

    assert refresco.toca_ciclo(None)
    assert not refresco.toca_ciclo(ultima, ultima + timedelta(seconds=10))
    assert refresco.toca_ciclo(ultima, ultima + timedelta(seconds=60))


def test_cada_ciclo_deja_una_linea_en_el_log(carpeta):
    refresco.ejecutar_ciclo(carpeta, "PRUEBA")

    ultima = config.LOG_REFRESCO.read_text(encoding="utf-8").strip().splitlines()[-1]
    assert "origen=PRUEBA" in ultima
    assert "pedidos=2/2" in ultima
    assert "estado=correcto" in ultima


def test_resultados_llevan_linaje(carpeta):
    ciclo = refresco.ejecutar_ciclo(carpeta, "PRUEBA")
    filtrados = analiticas.aplicar_filtros(ciclo["datos"], {"tipos": ["CUSTOM"]})

    tabla = analiticas.ventas_por_periodo(filtrados)
    exportada = con_linaje(tabla)

    assert {"origen", "fecha_corte", "ejecucion", "filtros", "filas_origen", "funcion"} <= set(tabla.attrs)
    assert exportada["linaje_filtros"].iloc[0] == "tipos=CUSTOM"
    assert exportada["linaje_ejecucion"].iloc[0] == f"{ciclo['comprobado']:%Y-%m-%d %H:%M:%S}"
    assert exportada["linaje_funcion"].iloc[0] == "ventas_por_periodo"


def test_cohortes_con_poca_muestra_no_calculables(carpeta):
    ciclo = refresco.ejecutar_ciclo(carpeta, "PRUEBA")

    tabla = analiticas.cohortes(ciclo["datos"])

    assert tabla.empty
    assert tabla.attrs["estado"].startswith("NO CALCULABLE")
