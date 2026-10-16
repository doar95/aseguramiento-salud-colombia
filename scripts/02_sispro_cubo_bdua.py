"""
Serie histórica mensual de afiliados por municipio y régimen a partir del extracto
del cubo BDUA publicado por SISPRO ("Construya su consulta - Aseguramiento").

Entrada : data/raw/sispro_cubo_bdua/municipio_regimen_estado_mensual.csv.gz
          (periodo AAAAMM, cod_municipio, régimen, estado de afiliación, afiliados)
          data/raw/sispro_cubo_bdua/geografia.csv
Salidas :
  sispro_afiliados_activos_municipio_mensual.csv   (municipio x mes; columnas por régimen,
                                                    solo estado "Activo" + "Proteccion Laboral"
                                                    y "Suspendido*", que siguen siendo afiliados)
  sispro_afiliados_activos_nacional_mensual.csv    (control de totales)

Nota: el cubo incluye registros "Retirado", "Afiliado fallecido", "Desafiliado" y
"Afiliación interrumpida" que NO son afiliados vigentes; se excluyen.

Uso: python scripts/02_sispro_cubo_bdua.py
"""
from pathlib import Path
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
RAW = RAIZ / "data" / "raw" / "sispro_cubo_bdua"
OUT = RAIZ / "data" / "processed"
OUT.mkdir(parents=True, exist_ok=True)

VIGENTES = {"Activo", "Activo por emergencia", "Proteccion Laboral", "Suspendido", "Suspendido por documento",
            "Suspendido por mora"}

df = pd.read_csv(RAW / "municipio_regimen_estado_mensual.csv.gz",
                 dtype={"periodo": str, "cod_municipio": str})
df["cod_municipio"] = df["cod_municipio"].str.zfill(5)
print("Estados presentes:", sorted(df["estado_afiliacion"].unique()))

vig = df[df["estado_afiliacion"].isin(VIGENTES)]
w = (vig.pivot_table(index=["periodo", "cod_municipio"], columns="regimen",
                     values="afiliados", aggfunc="sum", fill_value=0)
        .rename(columns=lambda c: c.lower().replace(" ", "_"))
        .reset_index())
w.columns.name = None
regs = [c for c in w.columns if c not in ("periodo", "cod_municipio")]
w["total"] = w[regs].sum(axis=1)
# Activos estrictos (sin suspendidos ni protección laboral), útiles para comparar con MinSalud
act = (df[df["estado_afiliacion"] == "Activo"]
       .groupby(["periodo", "cod_municipio"])["afiliados"].sum().rename("total_solo_activos"))
w = w.merge(act, on=["periodo", "cod_municipio"], how="left").fillna({"total_solo_activos": 0})

geo = pd.read_csv(RAW / "geografia.csv", dtype=str)
geo["municipio"] = geo["municipio"].str.replace(r"^\d{5}\s*-\s*", "", regex=True)
w = w.merge(geo[["cod_municipio", "departamento", "municipio", "categoria_ruralidad"]],
            on="cod_municipio", how="left")
w.insert(1, "anio", w["periodo"].str[:4].astype(int))
w.insert(2, "mes", w["periodo"].str[4:].astype(int))
w = w[["periodo", "anio", "mes", "cod_municipio", "departamento", "municipio",
       "categoria_ruralidad"] + regs + ["total", "total_solo_activos"]]
w.to_csv(OUT / "sispro_afiliados_activos_municipio_mensual.csv", index=False, encoding="utf-8")

nac = w.groupby("periodo")[regs + ["total", "total_solo_activos"]].sum().reset_index()
nac.to_csv(OUT / "sispro_afiliados_activos_nacional_mensual.csv", index=False, encoding="utf-8")
print(w.shape, "periodos:", w["periodo"].min(), "->", w["periodo"].max(), "| n =", w["periodo"].nunique())
print(nac.iloc[[0, 12, 60, 120, -13, -1]].to_string(index=False))
