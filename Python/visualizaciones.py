import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Patch
from matplotlib.ticker import FuncFormatter, MaxNLocator, PercentFormatter

import analiticas
import config
from utils.trazas import guardar_csv

COLOR_PRINCIPAL = (0.93, 0.27, 0.45)
COLOR_SECUNDARIO = (0.15, 0.17, 0.25)
COLOR_APOYO = (0.98, 0.65, 0.20)
COLOR_SUAVE = (0.80, 0.82, 0.86)
PALETA = [COLOR_PRINCIPAL, COLOR_SECUNDARIO, COLOR_APOYO, (0.30, 0.65, 0.80), (0.45, 0.75, 0.45), (0.60, 0.45, 0.80), (0.55, 0.55, 0.55)]

plt.rcParams.update({
    "figure.figsize": (11, 6),
    "figure.dpi": 110,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.titlesize": 15,
    "axes.titleweight": "bold",
    "axes.titlelocation": "left",
    "axes.labelsize": 11,
    "axes.grid": True,
    "grid.alpha": 0.25,
    "legend.frameon": False,
})


def euros(valor, _=None):
    return f"{valor:,.0f} €".replace(",", ".")


def periodo(datos):
    fechas = datos["pedidos"]["fecha_pedido"]
    return f"{fechas.min():%Y-%m} a {fechas.max():%Y-%m}"


def preparar_figura(titulo, datos, nota=""):
    figura, eje = plt.subplots()
    eje.set_title(titulo, pad=28)
    subtitulo = f"Datos {datos['origen']} · {periodo(datos)} · corte {datos['fecha_corte']:%Y-%m-%d}"
    if nota:
        subtitulo += f" · {nota}"
    eje.text(0, 1.02, subtitulo, transform=eje.transAxes, fontsize=10, color="0.4")
    return figura, eje


def serie_ingresos(datos):
    df = analiticas.ventas_por_periodo(datos)
    figura, eje = preparar_figura("Ingresos válidos por mes", datos, "solo pedidos CONFIRMADOS")
    completos = df[df["mes_completo"]]

    eje.plot(completos["mes"], completos["ingresos"], marker="o", color=COLOR_PRINCIPAL, linewidth=2.5, label="Ingresos del mes")
    eje.plot(df["mes"], df["media_movil_3_previos"], linestyle="--", color=COLOR_SECUNDARIO, label="Media de los 3 meses previos")
    incompletos = df[~df["mes_completo"]]
    if not incompletos.empty:
        eje.scatter(incompletos["mes"], incompletos["ingresos"], color=COLOR_SUAVE, zorder=3,
                    label="Mes en curso (incompleto)")
    eje.yaxis.set_major_formatter(FuncFormatter(euros))
    eje.set_ylabel("Ingresos (EUR)")
    eje.set_xlabel("Mes")
    eje.tick_params(axis="x", rotation=45)
    eje.legend()

    mejor = completos.loc[completos["ingresos"].idxmax()] if not completos.empty else None
    lectura = (f"El mes con más ingresos fue {mejor['mes']} con {euros(mejor['ingresos'])}. " "La línea discontinua usa solo meses anteriores, sin incluir el propio mes." if mejor is not None else "No hay meses completos con ventas.")
    return figura, df, lectura


def ranking_modelos(datos, maximo=12):
    df = analiticas.modelos_abc(datos)
    top = df[df["pares"] > 0].sort_values("pares", ascending=False).head(maximo).iloc[::-1]
    figura, eje = preparar_figura(f"Top {len(top)} modelos por pares vendidos", datos, "solo pedidos CONFIRMADOS")

    colores = [COLOR_PRINCIPAL if clase == "A" else COLOR_SECUNDARIO if clase == "B" else COLOR_SUAVE for clase in top["clase_abc"]]
    barras = eje.barh(top["modelo"], top["pares"], color=colores)
    eje.bar_label(barras, padding=4, fontsize=9)
    eje.set_xlabel("Pares vendidos")
    eje.grid(axis="y", visible=False)
    leyenda = [Patch(color=color, label=f"Clase {clase}") for clase, color in (("A", COLOR_PRINCIPAL), ("B", COLOR_SECUNDARIO), ("C", COLOR_SUAVE))]
    eje.legend(handles=leyenda, loc="lower right")

    lider = top.iloc[-1] if not top.empty else None
    lectura = (f"{lider['modelo']} es el modelo con más pares vendidos ({int(lider['pares'])}). " "El color indica la clase ABC calculada por ingresos, no por pares." if lider is not None else "No hay ventas en el periodo.")
    return figura, top.iloc[::-1], lectura


def pareto_modelos(datos):
    df = analiticas.modelos_abc(datos)
    df = df[df["ingresos"] > 0]
    figura, eje = preparar_figura("Pareto de ingresos por modelo", datos, "solo pedidos CONFIRMADOS")

    eje.bar(df["modelo"], df["ingresos"], color=COLOR_PRINCIPAL, label="Ingresos del modelo")
    eje.yaxis.set_major_formatter(FuncFormatter(euros))
    eje.set_ylabel("Ingresos (EUR)")
    eje.tick_params(axis="x", rotation=60)

    acumulado = eje.twinx()
    acumulado.plot(df["modelo"], df["acumulado_pct"], color=COLOR_SECUNDARIO, marker="o", label="% acumulado")
    acumulado.axhline(config.UMBRAL_ABC_A * 100, color=COLOR_APOYO, linestyle="--", label=f"Límite clase A ({config.UMBRAL_ABC_A:.0%})")
    acumulado.set_ylim(0, 105)
    acumulado.yaxis.set_major_formatter(PercentFormatter())
    acumulado.set_ylabel("% acumulado de ingresos")
    acumulado.grid(False)

    lineas = eje.get_legend_handles_labels()
    lineas_acumulado = acumulado.get_legend_handles_labels()
    eje.legend(lineas[0] + lineas_acumulado[0], lineas[1] + lineas_acumulado[1], loc="center right")

    clase_a = int((df["clase_abc"] == "A").sum())
    lectura = (f"{clase_a} de {len(df)} modelos con ventas generan hasta el {config.UMBRAL_ABC_A:.0%} de los " "ingresos (clase A): son los que no deben quedarse sin stock.")
    return figura, df, lectura


def histograma_ticket(datos):
    pedidos, _ = analiticas.ventas(datos)
    figura, eje = preparar_figura("Distribución del importe por pedido", datos, "solo pedidos CONFIRMADOS · eje X logarítmico")

    importes = pedidos.loc[pedidos["importe"] > 0, "importe"]
    bordes = np.logspace(np.log10(importes.min()), np.log10(importes.max()), 30) if len(importes) > 1 else 10
    for tipo, color in zip(config.TIPOS_PEDIDO, PALETA):
        del_tipo = pedidos.loc[(pedidos["tipo_pedido"] == tipo) & (pedidos["importe"] > 0), "importe"]
        if not del_tipo.empty:
            eje.hist(del_tipo, bins=bordes, color=color, alpha=0.75, edgecolor="white", label=tipo)
    media, mediana = pedidos["importe"].mean(), pedidos["importe"].median()
    eje.axvline(media, color=COLOR_APOYO, linestyle="--", linewidth=2, label=f"Media: {euros(media)}")
    eje.axvline(mediana, color=COLOR_APOYO, linewidth=2.5, label=f"Mediana: {euros(mediana)}")
    eje.set_xscale("log")
    eje.xaxis.set_major_formatter(FuncFormatter(euros))
    eje.set_xlabel("Importe del pedido (EUR, escala logarítmica)")
    eje.set_ylabel("Número de pedidos")
    eje.legend()

    lectura = (f"La media ({euros(media)}) es mayor que la mediana ({euros(mediana)}) porque unos pocos pedidos " "grandes estiran la distribución hacia la derecha; la mediana representa mejor el pedido típico." if media > mediana else f"Media ({euros(media)}) y mediana ({euros(mediana)}) están próximas: la distribución es simétrica.")
    return figura, pedidos[["id_pedido", "tipo_pedido", "importe"]], lectura


def boxplot_pares_tipo(datos):
    pedidos, _ = analiticas.ventas(datos)
    figura, eje = preparar_figura("Pares por pedido según tipo de pedido", datos, "solo pedidos CONFIRMADOS")

    tipos = [t for t in config.TIPOS_PEDIDO if (pedidos["tipo_pedido"] == t).any()]
    grupos = [pedidos.loc[pedidos["tipo_pedido"] == t, "pares"] for t in tipos]
    caja = eje.boxplot(grupos, tick_labels=tipos, patch_artist=True, widths=0.5, medianprops={"color": "white", "linewidth": 2})
    for parche, color in zip(caja["boxes"], PALETA):
        parche.set_facecolor(color)
    eje.set_ylabel("Pares por pedido")
    eje.set_xlabel("Tipo de pedido")

    medianas = {t: g.median() for t, g in zip(tipos, grupos)}
    lectura = ("Mediana de pares por pedido: " + ", ".join(f"{t} {m:g}" for t, m in medianas.items()) + ". Los puntos sueltos son atípicos según la regla IQR; se conservan, no se borran automáticamente.")
    return figura, pedidos[["id_pedido", "tipo_pedido", "pares"]], lectura


def mapa_calor_tallas(datos):
    df = analiticas.matriz_modelo_talla(datos, proporcion=True).set_index("modelo")
    figura, eje = preparar_figura("Reparto de tallas dentro de cada modelo", datos, "% de pares de cada modelo")
    figura.set_size_inches(12, max(4, 0.45 * len(df) + 2))

    imagen = eje.imshow(df.to_numpy(), aspect="auto", cmap="RdPu")
    eje.set_xticks(range(len(df.columns)), df.columns, rotation=90 if len(df.columns) > 15 else 0)
    eje.set_yticks(range(len(df.index)), df.index)
    eje.set_xlabel("Talla (EU)")
    eje.grid(False)
    barra = figura.colorbar(imagen, ax=eje)
    barra.set_label("% de pares del modelo")

    columna_max = df.mean().idxmax() if not df.empty else "-"
    lectura = (f"La talla {columna_max} concentra de media la mayor parte de los pares. Cada fila suma 100 %, " "así que se comparan tallas dentro de un modelo, no volúmenes entre modelos.")
    return figura, df.reset_index(), lectura


def dispersion_rfm(datos):
    df = analiticas.clientes_rfm(datos)
    figura, eje = preparar_figura("Clientes: frecuencia frente a gasto", datos, "segmentos RFM")

    for segmento, color in zip(sorted(df["segmento"].unique()), PALETA):
        grupo = df[df["segmento"] == segmento]
        eje.scatter(grupo["frequency"], grupo["monetary"], s=70, color=color, alpha=0.85, label=segmento,
                    edgecolor="white")
    eje.yaxis.set_major_formatter(FuncFormatter(euros))
    eje.xaxis.set_major_locator(MaxNLocator(integer=True))
    eje.set_xlabel("Pedidos confirmados del cliente (frequency)")
    eje.set_ylabel("Gasto total (EUR)")
    eje.legend(title="Segmento RFM")

    variable = len(df) > 2 and df["frequency"].nunique() > 1 and df["monetary"].nunique() > 1
    correlacion = df["frequency"].corr(df["monetary"]) if variable else np.nan
    lectura = (f"Correlación entre pedidos y gasto: {correlacion:.2f} (de -1 a 1). Los puntos alejados de la nube son " "clientes que gastan mucho con pocos pedidos o al revés." if not np.isnan(correlacion) else "Hay muy pocos clientes o todos tienen el mismo número de pedidos: no se puede calcular una " "correlación fiable.")
    return figura, df[["id_cliente", "frequency", "monetary", "recency_dias", "segmento"]], lectura


def comparativa_tipos(datos):
    df = analiticas.custom_vs_estandar(datos)
    figura, eje = preparar_figura("Peso de Custom y estándar", datos, "% sobre el total de ventas válidas")

    medidas = ["peso_pedidos_venta_pct", "peso_pares_pct", "peso_ingresos_pct"]
    etiquetas = ["Pedidos", "Pares", "Ingresos"]
    posiciones = np.arange(len(medidas))
    ancho = 0.38
    for i, (_, fila) in enumerate(df.iterrows()):
        barras = eje.bar(posiciones + (i - 0.5) * ancho, fila[medidas].astype(float), ancho, color=PALETA[i], label=fila["tipo_pedido"])
        eje.bar_label(barras, fmt="%.1f %%", padding=3, fontsize=9)
    eje.set_xticks(posiciones, etiquetas)
    eje.yaxis.set_major_formatter(PercentFormatter())
    eje.set_ylim(0, 110)
    eje.set_ylabel("% del total")
    eje.legend(title="Tipo de pedido")

    custom = df.set_index("tipo_pedido").loc["CUSTOM"]
    lectura = (f"Los pedidos Custom son el {custom['peso_pedidos_venta_pct']:.1f} % de los pedidos y aportan el " f"{custom['peso_ingresos_pct']:.1f} % de los ingresos.")
    if custom["peso_ingresos_pct"] > custom["peso_pedidos_venta_pct"]:
        lectura += " Son menos pedidos, pero de mayor importe."
    return figura, df, lectura


FIGURAS = {
    "01_serie_ingresos_mensuales": serie_ingresos,
    "02_ranking_modelos_pares": ranking_modelos,
    "03_pareto_ingresos_modelos": pareto_modelos,
    "04_histograma_importe_pedido": histograma_ticket,
    "05_boxplot_pares_por_tipo": boxplot_pares_tipo,
    "06_mapa_calor_modelo_talla": mapa_calor_tallas,
    "07_dispersion_clientes_rfm": dispersion_rfm,
    "08_comparativa_custom_estandar": comparativa_tipos,
}


def guardar_figuras(datos, carpeta):
    carpeta.mkdir(parents=True, exist_ok=True)
    lecturas = []
    for nombre, funcion in FIGURAS.items():
        figura, _, lectura = funcion(datos)
        figura.tight_layout()
        figura.savefig(carpeta / f"{nombre}.png", bbox_inches="tight")
        plt.close(figura)
        lecturas.append({"figura": f"{nombre}.png", "lectura": lectura})
    tabla = pd.DataFrame(lecturas)
    guardar_csv(tabla, carpeta / "lecturas.csv")
    return tabla