import pandas as pd
import pytest

import config

DATOS = {
    "clientes": [
        {"id_cliente": "1", "ref_odoo": "CLI-001", "tipo": "CLUB", "ciudad": "Madrid", "activo": "True", "fecha_alta": "2026-01-10"},
        {"id_cliente": "2", "ref_odoo": "CLI-002", "tipo": "PARTICULAR", "ciudad": "Getafe", "activo": "True", "fecha_alta": "2026-02-15"},
    ],
    "modelos": [
        {"id_modelo": "1", "ref_odoo": "SF-001", "nombre": "Cometa", "categoria": "correr", "precio_base": "70.00", "personalizable": "True", "activo": "True"},
        {"id_modelo": "2", "ref_odoo": "SF-002", "nombre": "Titan", "categoria": "botas", "precio_base": "90.00", "personalizable": "False", "activo": "True"},
    ],
    "pedidos": [
        {"id_pedido": "1", "ref_odoo": "CUS-0001", "tipo": "CUSTOM", "estado": "CONFIRMADO", "fecha_pedido": "2026-10-01 10:00:00", "fecha_entrega_prevista": "2026-10-20", "fecha_confirmacion": "2026-10-02 09:00:00", "fecha_cancelacion": "NULL", "total": "350.00","id_cliente": "1"},
        {"id_pedido": "2", "ref_odoo": "PED-0001", "tipo": "ESTANDAR", "estado": "CANCELADO", "fecha_pedido": "2026-10-05 12:00:00", "fecha_entrega_prevista": "NULL", "fecha_confirmacion": "2026-10-05 13:00:00", "fecha_cancelacion": "2026-10-06 10:00:00", "total": "90.00", "id_cliente": "2"},
    ],
    "lineas": [
        {"id_linea": "1", "id_pedido": "1", "id_variante": "1", "id_modelo": "1", "color": "negro", "talla": "40.0", "cantidad": "2", "precio_unitario": "70.00", "logo_club": "True", "personalizada": "True"},
        {"id_linea": "2", "id_pedido": "1", "id_variante": "1", "id_modelo": "1", "color": "negro", "talla": "41.0", "cantidad": "3", "precio_unitario": "70.00", "logo_club": "True", "personalizada": "True"},
        {"id_linea": "3", "id_pedido": "2", "id_variante": "2", "id_modelo": "2", "color": "blanco", "talla": "42.0", "cantidad": "1", "precio_unitario": "90.00", "logo_club": "False", "personalizada": "False"},
    ],
    "stock": [
        {"id_variante": "1", "id_modelo": "1", "color": "negro", "talla": "40.0", "cantidad": "10", "stock_minimo": "5", "ultima_actualizacion": "2026-11-01 08:00:00"},
        {"id_variante": "1", "id_modelo": "1", "color": "negro", "talla": "41.0", "cantidad": "8", "stock_minimo": "5", "ultima_actualizacion": "2026-11-01 08:00:00"},
        {"id_variante": "2", "id_modelo": "2", "color": "blanco", "talla": "42.0", "cantidad": "4", "stock_minimo": "5", "ultima_actualizacion": "2026-11-01 08:00:00"},
    ],
}


def escribir(carpeta, tabla, df):
    df.to_csv(carpeta / config.FICHEROS[tabla], index=False, encoding="utf-8")


def leer(carpeta, tabla):
    return pd.read_csv(carpeta / config.FICHEROS[tabla], dtype=str, keep_default_na=False)


@pytest.fixture
def carpeta(tmp_path):
    for tabla, filas in DATOS.items():
        escribir(tmp_path, tabla, pd.DataFrame(filas))
    return tmp_path