import argparse

import numpy as np
import pandas as pd

import config
from utils.trazas import guardar_csv

FECHA_INICIO = pd.Timestamp("2024-11-01")
MESES = 24
NUM_CLIENTES = 60
CLIENTES_INICIALES = 35
PEDIDOS_POR_MES = 55
FECHA_STOCK = "2026-11-01 08:00:00"
RECARGO_CUSTOM = 12.00
SUBIDA_ANUAL = 0.03
PROB_PEDIDO_GRANDE = 0.03

MODELOS = [
    ("Cometa", "correr", 69.99, None, None),
    ("Relámpago", "correr", 119.99, None, None),
    ("Impulso", "correr", 49.99, None, "2026-03"),
    ("Lince", "correr", 84.99, None, None),
    ("Nova Run", "correr", 99.99, "2025-09", None),
    ("Titán", "botas", 99.99, None, None),
    ("Granito", "botas", 89.99, None, None),
    ("Ventisca", "botas", 114.99, "2026-02", None),
    ("Pantera GK", "futbol", 79.99, None, None),
    ("Furia FG", "futbol", 109.99, None, None),
    ("Saeta 3", "futbol", 64.99, None, None),
    ("Halcón SG", "futbol", 94.99, None, None),
    ("Coloso", "baloncesto", 129.99, None, None),
    ("Rayo X", "baloncesto", 94.99, None, None),
    ("Ciclón Mid", "baloncesto", 74.99, None, None),
    ("Vértigo", "baloncesto", 89.99, None, None),
]
COLORES = ["negro", "blanco"]

ESTACIONALIDAD = {
    "correr": [1.0, 0.9, 1.0, 1.2, 1.4, 1.3, 1.0, 0.8, 0.8, 0.9, 0.9, 0.8],
    "botas": [1.3, 0.9, 0.8, 0.7, 0.7, 0.6, 0.6, 0.7, 1.5, 1.4, 1.1, 1.0],
    "futbol": [1.3, 0.9, 0.8, 0.7, 0.7, 0.6, 0.6, 0.7, 1.5, 1.4, 1.1, 1.0],
    "baloncesto": [0.9, 0.9, 0.9, 0.8, 0.8, 0.7, 0.7, 0.9, 1.2, 1.4, 1.3, 1.2],
}
FACTOR_CAMPANA = {11: 1.35, 1: 1.15}
TIPOS_CLIENTE = {"CLUB": 0.30, "EQUIPO": 0.20, "EMPRESA": 0.15, "PARTICULAR": 0.35}
PROB_CUSTOM = {"CLUB": 0.70, "EQUIPO": 0.60, "EMPRESA": 0.40, "PARTICULAR": 0.05}
PROB_CANCELACION = {"CUSTOM": 0.12, "ESTANDAR": 0.08}
CIUDADES = ["Madrid", "Getafe", "Alcalá de Henares", "Toledo", "Segovia", "Guadalajara", "Leganés", "Móstoles",
            "Fuenlabrada", "Ávila"]


def indice_mes(texto):
    if texto is None:
        return None
    periodo = pd.Period(texto, freq="M")
    return (periodo - pd.Period(FECHA_INICIO, freq="M")).n


def tallas_de(categoria):
    if categoria == "correr":
        return np.arange(35, 46.5, 0.5)
    return np.arange(35, 47, 1.0)


def generar_modelos(rng):
    filas = []
    for i, (nombre, categoria, precio, lanzamiento, retirada) in enumerate(MODELOS, start=1):
        filas.append({
            "id_modelo": i, "ref_odoo": f"SF-{i:03d}", "nombre": nombre, "categoria": categoria,
            "precio_base": precio, "personalizable": categoria != "correr", "activo": retirada is None,
            "mes_alta": indice_mes(lanzamiento) or 0,
            "mes_baja": indice_mes(retirada) if retirada else MESES,
        })
    modelos = pd.DataFrame(filas)
    modelos["popularidad"] = rng.dirichlet(np.full(len(modelos), 1.5))
    return modelos


def generar_variantes(modelos):
    filas = []
    for _, modelo in modelos.iterrows():
        for color in COLORES:
            filas.append({"id_variante": len(filas) + 1, "id_modelo": modelo["id_modelo"], "color": color, "categoria": modelo["categoria"]})
    return pd.DataFrame(filas)


def generar_clientes(rng):
    tipos = rng.choice(list(TIPOS_CLIENTE), size=NUM_CLIENTES, p=list(TIPOS_CLIENTE.values()))
    mes_alta = np.zeros(NUM_CLIENTES, dtype=int)
    mes_alta[CLIENTES_INICIALES:] = np.sort(rng.integers(1, MESES - 2, NUM_CLIENTES - CLIENTES_INICIALES))

    abandona = rng.random(NUM_CLIENTES) < 0.20
    mes_baja = np.where(abandona, np.minimum(mes_alta + rng.integers(6, 15, NUM_CLIENTES), MESES), MESES)

    clientes = pd.DataFrame({
        "id_cliente": np.arange(1, NUM_CLIENTES + 1),
        "ref_odoo": [f"CLI-{i:03d}" for i in range(1, NUM_CLIENTES + 1)],
        "tipo": tipos,
        "ciudad": rng.choice(CIUDADES, size=NUM_CLIENTES),
        "activo": mes_baja == MESES,
        "mes_alta": mes_alta,
        "mes_baja": mes_baja,
    })
    clientes["peso"] = rng.pareto(2.5, NUM_CLIENTES) + 0.3
    return clientes


def elegir_tallas(rng, categoria, cantidad, distintas):
    tallas = tallas_de(categoria)
    probabilidades = np.exp(-0.5 * ((tallas - 41) / 2.2) ** 2)
    probabilidades /= probabilidades.sum()
    cantidad = min(cantidad, len(tallas))
    return rng.choice(tallas, size=cantidad, replace=not distintas, p=probabilidades)


def precio_linea(precio_actual, fecha, custom):
    precio = precio_actual / (1 + SUBIDA_ANUAL) ** (pd.Timestamp("2026-01-01").year - fecha.year)
    if not custom and fecha.month == 11 and fecha.day >= 24:
        precio *= 0.75
    elif not custom and fecha.month == 1 and fecha.day <= 15:
        precio *= 0.80
    if custom:
        precio += RECARGO_CUSTOM
    return round(precio, 2)


def minutos_del_mes(rng, inicio, num_pedidos):
    dias = inicio.days_in_month
    minutos = rng.integers(0, dias * 24 * 60, num_pedidos)
    if inicio.month == 11:
        black_friday = rng.random(num_pedidos) < 0.35
        minutos[black_friday] = rng.integers(23 * 24 * 60, dias * 24 * 60, black_friday.sum())
    return np.sort(minutos)


def generar_pedidos(rng, clientes, modelos, variantes):
    pedidos, lineas = [], []
    fin = FECHA_INICIO + pd.DateOffset(months=MESES)

    for mes in range(MESES):
        inicio = FECHA_INICIO + pd.DateOffset(months=mes)
        disponibles = modelos[(modelos["mes_alta"] <= mes) & (modelos["mes_baja"] > mes)]
        activos = clientes[(clientes["mes_alta"] <= mes) & (clientes["mes_baja"] > mes)]

        factor_mes = np.mean([ESTACIONALIDAD[c][inicio.month - 1] for c in disponibles["categoria"]])
        factor_mes *= FACTOR_CAMPANA.get(inicio.month, 1.0)
        tendencia = 1 + 0.015 * mes
        num_pedidos = rng.poisson(PEDIDOS_POR_MES * factor_mes * tendencia * len(activos) / CLIENTES_INICIALES)

        estacion = disponibles["categoria"].map(lambda c: ESTACIONALIDAD[c][inicio.month - 1])
        peso_modelos = (disponibles["popularidad"] * estacion).to_numpy()
        peso_modelos = peso_modelos / peso_modelos.sum()
        peso_clientes = (activos["peso"] / activos["peso"].sum()).to_numpy()

        for minuto in minutos_del_mes(rng, inicio, num_pedidos):
            id_pedido = len(pedidos) + 1
            cliente = activos.iloc[rng.choice(len(activos), p=peso_clientes)]
            custom = rng.random() < PROB_CUSTOM[cliente["tipo"]]
            fecha = inicio + pd.Timedelta(minutes=int(minuto))
            grande = custom and cliente["tipo"] == "CLUB" and rng.random() < PROB_PEDIDO_GRANDE

            if custom:
                elegidos = rng.choice(disponibles.index, size=1, p=peso_modelos)
                num_tallas = int(rng.integers(8, 11)) if grande else int(rng.integers(3, 9))
            else:
                elegidos = rng.choice(disponibles.index, size=int(rng.integers(1, 4)), p=peso_modelos)
                num_tallas = 1

            usadas = set()
            for indice in elegidos:
                modelo = disponibles.loc[indice]
                opciones = variantes[variantes["id_modelo"] == modelo["id_modelo"]]["id_variante"].to_numpy()
                id_variante = int(rng.choice(opciones))
                precio = precio_linea(modelo["precio_base"], fecha, custom)
                for talla in elegir_tallas(rng, modelo["categoria"], num_tallas, distintas=custom):
                    if (id_variante, talla) in usadas:
                        continue
                    usadas.add((id_variante, talla))
                    if grande:
                        cantidad = int(rng.integers(10, 21))
                    elif custom:
                        cantidad = int(rng.integers(2, 11))
                    else:
                        cantidad = int(rng.choice([1, 1, 1, 2]))
                    lineas.append({
                        "id_linea": len(lineas) + 1, "id_pedido": id_pedido, "id_variante": id_variante,
                        "id_modelo": int(modelo["id_modelo"]), "color": COLORES[(id_variante - 1) % len(COLORES)],
                        "talla": float(talla), "cantidad": cantidad, "precio_unitario": precio,
                        "logo_club": custom and cliente["tipo"] in ("CLUB", "EQUIPO"), "personalizada": custom,
                    })

            tipo = "CUSTOM" if custom else "ESTANDAR"
            reciente = (fin - fecha).days <= 21
            prob_borrador = 0.35 if reciente else 0.06
            prob_cancelado = PROB_CANCELACION[tipo]
            estado = rng.choice(["CONFIRMADO", "CANCELADO", "BORRADOR"],
                                p=[1 - prob_borrador - prob_cancelado, prob_cancelado, prob_borrador])

            confirmacion = fecha + pd.Timedelta(hours=int(rng.integers(1, 48)))
            dias_entrega = int(rng.integers(20, 36) if custom else rng.integers(3, 13))
            pedidos.append({
                "id_pedido": id_pedido,
                "ref_odoo": f"{'CUS' if custom else 'PED'}-{id_pedido:04d}",
                "tipo": tipo,
                "estado": estado,
                "fecha_pedido": fecha,
                "fecha_entrega_prevista": None if estado == "BORRADOR" else
                (fecha + pd.Timedelta(days=dias_entrega)).normalize(),
                "fecha_confirmacion": None if estado == "BORRADOR" else confirmacion,
                "fecha_cancelacion": confirmacion + pd.Timedelta(days=int(rng.integers(1, 10)))
                if estado == "CANCELADO" else None,
                "id_cliente": int(cliente["id_cliente"]),
            })

    pedidos = pd.DataFrame(pedidos)
    lineas = pd.DataFrame(lineas)
    importes = (lineas["cantidad"] * lineas["precio_unitario"]).groupby(lineas["id_pedido"]).sum().round(2)
    pedidos["total"] = pedidos["id_pedido"].map(importes)
    return pedidos, lineas


def generar_stock(rng, modelos, variantes):
    filas = []
    modelos = modelos.set_index("id_modelo")
    for _, variante in variantes.iterrows():
        modelo = modelos.loc[variante["id_modelo"]]
        media = 0 if not modelo["activo"] else 10 + 120 * modelo["popularidad"]
        for talla in tallas_de(variante["categoria"]):
            filas.append({"id_variante": variante["id_variante"], "id_modelo": variante["id_modelo"], "color": variante["color"], "talla": float(talla), "cantidad": int(rng.poisson(media)), "stock_minimo": 5, "ultima_actualizacion": FECHA_STOCK})
    return pd.DataFrame(filas)


def generar(semilla=config.SEMILLA):
    rng = np.random.default_rng(semilla)
    modelos = generar_modelos(rng)
    variantes = generar_variantes(modelos)
    clientes = generar_clientes(rng)
    pedidos, lineas = generar_pedidos(rng, clientes, modelos, variantes)
    stock = generar_stock(rng, modelos, variantes)

    alta_teorica = clientes["mes_alta"].map(lambda m: FECHA_INICIO + pd.DateOffset(months=int(m)))
    primera_compra = clientes["id_cliente"].map(pedidos.groupby("id_cliente")["fecha_pedido"].min())
    alta = primera_compra.fillna(alta_teorica).combine(alta_teorica, min)
    clientes["fecha_alta"] = (alta - pd.to_timedelta(rng.integers(1, 30, NUM_CLIENTES), unit="D")).dt.normalize()

    return {
        "clientes": clientes[config.COLUMNAS_OBLIGATORIAS["clientes"]],
        "modelos": modelos[config.COLUMNAS_OBLIGATORIAS["modelos"]],
        "pedidos": pedidos[config.COLUMNAS_OBLIGATORIAS["pedidos"]],
        "lineas": lineas[config.COLUMNAS_OBLIGATORIAS["lineas"]],
        "stock": stock[config.COLUMNAS_OBLIGATORIAS["stock"]],
    }


def introducir_errores(tablas):
    tablas = {nombre: df.copy().astype(object) for nombre, df in tablas.items()}
    pedidos, lineas, stock = tablas["pedidos"], tablas["lineas"], tablas["stock"]
    errores = []

    def anotar(tabla, registro, regla, texto):
        errores.append({"tabla": tabla, "registro": registro, "regla": regla, "error_introducido": texto})

    anotar("pedidos", pedidos.at[0, "id_pedido"], "03", "id_cliente inexistente (999)")
    pedidos.at[0, "id_cliente"] = 999
    anotar("pedidos", pedidos.at[1, "id_pedido"], "04", "fecha_pedido imposible (2026-13-45)")
    pedidos.at[1, "fecha_pedido"] = "2026-13-45"
    anotar("pedidos", pedidos.at[2, "id_pedido"], "07", "estado fuera de catálogo (ENVIADO)")
    pedidos.at[2, "estado"] = "ENVIADO"
    anotar("pedidos", pedidos.at[3, "id_pedido"], "07", "tipo fuera de catálogo (MAYORISTA)")
    pedidos.at[3, "tipo"] = "MAYORISTA"
    anotar("pedidos", pedidos.at[4, "id_pedido"], "09", "id_cliente vacío")
    pedidos.at[4, "id_cliente"] = None
    anotar("pedidos", pedidos.at[5, "id_pedido"], "12", "total que no coincide con sus líneas")
    pedidos.at[5, "total"] = 1.0
    confirmado = pedidos.index[pedidos["estado"] == "CONFIRMADO"][10]
    anotar("pedidos", pedidos.at[confirmado, "id_pedido"], "12", "fecha de cancelación en un pedido confirmado")
    pedidos.at[confirmado, "fecha_cancelacion"] = pedidos.at[confirmado, "fecha_confirmacion"]

    anotar("lineas", lineas.at[500, "id_linea"], "03", "id_pedido inexistente (99999)")
    lineas.at[500, "id_pedido"] = 99999
    anotar("lineas", lineas.at[600, "id_linea"], "05", "cantidad negativa (-3)")
    lineas.at[600, "cantidad"] = -3
    anotar("lineas", lineas.at[700, "id_linea"], "06", "precio_unitario no numérico (abc)")
    lineas.at[700, "precio_unitario"] = "abc"
    anotar("lineas", lineas.at[800, "id_linea"], "08", "talla fuera de rango (60)")
    lineas.at[800, "talla"] = 60.0
    anotar("lineas", lineas.at[900, "id_linea"], "09", "id_modelo vacío")
    lineas.at[900, "id_modelo"] = None
    anotar("lineas", lineas.at[1000, "id_linea"], "02", "id_linea duplicado con datos distintos")
    duplicada = lineas.loc[[1000]].assign(cantidad=99)
    nuevo_id = int(lineas["id_linea"].max()) + 1
    anotar("lineas", nuevo_id, "10", "línea repetida con el mismo pedido, variante y talla")
    repetida = lineas.loc[[1100]].assign(id_linea=nuevo_id)
    tablas["lineas"] = pd.concat([lineas, duplicada, repetida], ignore_index=True)

    anotar("stock", f"{stock.at[0, 'id_variante']}-{stock.at[0, 'talla']}", "11", "stock negativo (-4)")
    stock.at[0, "cantidad"] = -4
    anotar("stock", f"{stock.at[1, 'id_variante']}-{stock.at[1, 'talla']}", "11", "variante y talla duplicadas con distinta cantidad")
    tablas["stock"] = pd.concat([stock, stock.loc[[1]].assign(cantidad=1)], ignore_index=True)

    return tablas, pd.DataFrame(errores)


def guardar(tablas, carpeta):
    for nombre, df in tablas.items():
        salida = df.copy()
        for columna in config.COLUMNAS_FECHA[nombre]:
            fechas = pd.to_datetime(salida[columna], errors="coerce")
            texto = fechas.dt.strftime("%Y-%m-%d" if columna in ("fecha_alta", "fecha_entrega_prevista") else "%Y-%m-%d %H:%M:%S")
            salida[columna] = texto.where(fechas.notna(), salida[columna])
        salida = salida.astype(object).where(salida.notna(), "NULL")
        guardar_csv(salida, carpeta / config.FICHEROS[nombre])


def resumen(tablas, semilla):
    pedidos, lineas = tablas["pedidos"], tablas["lineas"]
    meses = pedidos["fecha_pedido"].dt.to_period("M")
    filas = [
        ("origen", "SINTETICO"),
        ("semilla", semilla),
        ("periodo", f"{meses.min()} a {meses.max()}"),
        ("meses", meses.nunique()),
        ("clientes", len(tablas["clientes"])),
        ("clientes_con_pedidos", pedidos["id_cliente"].nunique()),
        ("modelos", len(tablas["modelos"])),
        ("pedidos", len(pedidos)),
        ("pedidos_custom", int((pedidos["tipo"] == "CUSTOM").sum())),
        ("lineas", len(lineas)),
        ("pares", int(lineas["cantidad"].sum())),
        ("filas_stock", len(tablas["stock"])),
    ]
    return pd.DataFrame(filas, columns=["parametro", "valor"])


if __name__ == "__main__":
    argumentos = argparse.ArgumentParser(description="Genera el histórico sintético de Sneaker Factory")
    argumentos.add_argument("--semilla", type=int, default=config.SEMILLA)
    semilla = argumentos.parse_args().semilla

    tablas = generar(semilla)
    guardar(tablas, config.ENTRADA_SINTETICA)
    datos = resumen(tablas, semilla)
    guardar_csv(datos, config.ENTRADA_SINTETICA / "resumen_generacion.csv")

    con_errores, errores = introducir_errores(tablas)
    guardar(con_errores, config.ENTRADA_SINTETICA_ERRORES)
    guardar_csv(errores, config.ENTRADA_SINTETICA_ERRORES / "errores_introducidos.csv")

    print(datos.to_string(index=False))
    print(f"\nErrores introducidos en la copia: {len(errores)}")