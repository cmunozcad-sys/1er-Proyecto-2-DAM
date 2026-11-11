import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

import analiticas
import config

PREDICTORES_NUMERICOS = ["demanda_mes_anterior", "media_3_meses_previos", "mes_seno", "mes_coseno"]
PREDICTOR_MODELO = ["id_modelo"]
OBJETIVO = "unidades_modelo_mes"


def construir_dataset(datos):
    df = analiticas.demanda_modelo_mes(datos)
    periodo = pd.PeriodIndex(df["mes"], freq="M")
    df = df[periodo.end_time < datos["fecha_corte"]].copy()

    ventas_previas = df.groupby("id_modelo")[OBJETIVO].transform(lambda s: s.shift(1).cumsum())
    df = df[ventas_previas > 0].dropna(subset=["demanda_mes_anterior", "media_3_meses_previos"])

    df["mes_seno"] = np.sin(2 * np.pi * df["mes_del_anio"] / 12)
    df["mes_coseno"] = np.cos(2 * np.pi * df["mes_del_anio"] / 12)
    nombres = datos["modelos"].set_index("id_modelo")["nombre"]
    df["modelo"] = df["id_modelo"].map(nombres)
    return df.sort_values(["mes", "id_modelo"]).reset_index(drop=True)


def separar_por_fecha(df):
    meses = sorted(df["mes"].unique())
    prueba = meses[-config.MESES_PRUEBA:]
    return df[~df["mes"].isin(prueba)], df[df["mes"].isin(prueba)]


def crear_regresor():
    preparacion = ColumnTransformer([
        ("numericas", "passthrough", PREDICTORES_NUMERICOS),
        ("modelo", OneHotEncoder(handle_unknown="ignore"), PREDICTOR_MODELO),
    ])
    bosque = RandomForestRegressor(n_estimators=300, max_depth=6, min_samples_leaf=3, random_state=config.SEMILLA)
    return Pipeline([("preparacion", preparacion), ("bosque", bosque)])


def errores(real, estimado):
    return mean_absolute_error(real, estimado), float(np.sqrt(mean_squared_error(real, estimado)))


def evaluar_prediccion(datos):
    df = construir_dataset(datos)
    meses = df["mes"].nunique()
    vacio = {"metricas": pd.DataFrame(), "por_modelo": pd.DataFrame(), "serie": pd.DataFrame(),
             "detalle": pd.DataFrame()}

    if meses < config.MESES_MINIMOS_PREDICCION:
        estado = (f"NO CALCULABLE: hay {meses} meses completos con demanda previa y hacen falta al menos "
                  f"{config.MESES_MINIMOS_PREDICCION}. Usar el histórico sintético para demostrar el método.")
        return {**vacio, "estado": estado}

    entrenamiento, prueba = separar_por_fecha(df)
    regresor = crear_regresor().fit(entrenamiento[PREDICTORES_NUMERICOS + PREDICTOR_MODELO],
                                    entrenamiento[OBJETIVO])

    prueba = prueba.copy()
    prueba["baseline"] = prueba["demanda_mes_anterior"]
    prueba["prediccion"] = regresor.predict(prueba[PREDICTORES_NUMERICOS + PREDICTOR_MODELO]).round(1)

    mae_base, rmse_base = errores(prueba[OBJETIVO], prueba["baseline"])
    mae_modelo, rmse_modelo = errores(prueba[OBJETIVO], prueba["prediccion"])
    metricas = pd.DataFrame([
        {"modelo": "baseline", "descripcion": "repite las unidades del mes anterior", "mae": mae_base,
         "rmse": rmse_base},
        {"modelo": "RandomForestRegressor", "descripcion": "300 árboles, profundidad máxima 6", "mae": mae_modelo,
         "rmse": rmse_modelo},
    ])
    metricas["mejora_mae_pct"] = (mae_base - metricas["mae"]) / mae_base * 100 if mae_base else np.nan
    metricas = metricas.round(2)

    por_modelo = prueba.groupby(["id_modelo", "modelo"]).apply(
        lambda g: pd.Series({
            "unidades_reales": int(g[OBJETIVO].sum()),
            "mae_baseline": mean_absolute_error(g[OBJETIVO], g["baseline"]),
            "mae_modelo": mean_absolute_error(g[OBJETIVO], g["prediccion"]),
        }), include_groups=False).reset_index().round(2)
    por_modelo["mejor"] = np.where(por_modelo["mae_modelo"] < por_modelo["mae_baseline"], "modelo", "baseline")
    por_modelo = por_modelo.sort_values("mae_modelo", ascending=False).reset_index(drop=True)

    historico = df.groupby("mes")[OBJETIVO].sum().rename("real")
    previsto = prueba.groupby("mes")[["baseline", "prediccion"]].sum()
    serie = historico.to_frame().join(previsto).reset_index()
    serie["conjunto"] = np.where(serie["mes"].isin(prueba["mes"]), "prueba", "entrenamiento")

    peor = por_modelo.iloc[0]
    if mae_modelo < mae_base:
        resumen = (f"El modelo mejora al baseline: MAE {mae_modelo:.1f} frente a {mae_base:.1f} pares por modelo y "
                   "mes.")
    else:
        resumen = (f"El modelo NO mejora al baseline (MAE {mae_modelo:.1f} frente a {mae_base:.1f}): con este "
                   "histórico, repetir el mes anterior es igual de útil y más sencillo.")
    estado = (f"CALCULADO con datos {datos['origen']}: entrenamiento {entrenamiento['mes'].min()} a "
              f"{entrenamiento['mes'].max()} ({len(entrenamiento)} filas), prueba {prueba['mes'].min()} a "
              f"{prueba['mes'].max()} ({len(prueba)} filas). {resumen} Mayor error: {peor['modelo']} "
              f"(MAE {peor['mae_modelo']:.1f}).")

    detalle = prueba[["mes", "id_modelo", "modelo", OBJETIVO, "baseline", "prediccion"]].rename(
        columns={OBJETIVO: "real"})
    return {"estado": estado, "metricas": metricas, "por_modelo": por_modelo, "serie": serie, "detalle": detalle}


def figura_real_vs_prediccion(resultado, datos):
    serie = resultado["serie"]
    figura, eje = plt.subplots(figsize=(11, 6))
    eje.set_title("Pares vendidos: real frente a predicción", loc="left", fontweight="bold", pad=28)
    eje.text(0, 1.02, f"Datos {datos['origen']} · suma de todos los modelos · últimos {config.MESES_PRUEBA} meses "
             "reservados para prueba", transform=eje.transAxes, fontsize=10, color="0.4")

    eje.plot(serie["mes"], serie["real"], marker="o", color=(0.15, 0.17, 0.25), label="Real")
    eje.plot(serie["mes"], serie["baseline"], marker="s", linestyle="--", color=(0.98, 0.65, 0.20),
             label="Baseline (mes anterior)")
    eje.plot(serie["mes"], serie["prediccion"], marker="D", color=(0.93, 0.27, 0.45), label="RandomForest")
    inicio_prueba = serie.index[serie["conjunto"] == "prueba"].min()
    eje.axvspan(inicio_prueba - 0.5, len(serie) - 0.5, color="0.9", zorder=0, label="Meses de prueba")
    eje.set_ylabel("Pares vendidos")
    eje.set_xlabel("Mes")
    eje.tick_params(axis="x", rotation=45)
    eje.spines[["top", "right"]].set_visible(False)
    eje.grid(alpha=0.25)
    eje.legend(frameon=False)
    figura.tight_layout()
    return figura
