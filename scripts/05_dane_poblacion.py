"""
Población DANE por municipio y grupo etario de la UPC (total del municipio, sin
distinguir área: cabecera + centros poblados y rural disperso).

Entradas (descargar del DANE, ver docs/guia_descarga.md; no se versionan por su tamaño):
  data/raw/dane/PPED-AreaSexoEdadMun-2018-2042_VP.xlsx          (actualización 30-jul-2025)
  data/raw/dane/DCD-area-sexo-edad-proypoblacion-Mun-2005-2017_VP.xlsx (retroproyecciones)
Salidas:
  data/processed/dane_poblacion_municipio_grupo_upc.csv   (cod_municipio x año x grupo UPC)
  data/processed/dane_poblacion_municipio_total.csv       (cod_municipio x año: total, hombres, mujeres)

Los grupos replican los de las resoluciones de UPC: <1, 1-4, 5-14, 15-18 H/M, 19-44 H/M,
45-49, ..., 70-74, 75+. Se construyen sumando edades simples. No se usa para repartir
afiliados: sirve como denominador y para comparar estructuras de edad.

Uso: python scripts/05_dane_poblacion.py [anio_desde] [anio_hasta]   (por defecto 2013 2030)
"""
from pathlib import Path
import re
import sys
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
RAW = RAIZ / "data" / "raw" / "dane"
OUT = RAIZ / "data" / "processed"
DESDE, HASTA = (int(sys.argv[1]), int(sys.argv[2])) if len(sys.argv) > 2 else (2013, 2030)

GRUPOS = [("<1", 0, 0, None), ("1-4", 1, 4, None), ("5-14", 5, 14, None),
          ("15-18H", 15, 18, "H"), ("15-18M", 15, 18, "M"), ("19-44H", 19, 44, "H"),
          ("19-44M", 19, 44, "M"), ("45-49", 45, 49, None), ("50-54", 50, 54, None),
          ("55-59", 55, 59, None), ("60-64", 60, 64, None), ("65-69", 65, 69, None),
          ("70-74", 70, 74, None), ("75+", 75, 200, None)]


def edad_sexo(col):
    """'Hombres 15 años' / 'Hombres_15' / 'Mujeres 100 años y más' -> ('H', 15)"""
    c = str(col)
    m = re.match(r"(Hombres|Mujeres)[ _](\d+)", c)
    return (c[0], int(m.group(2))) if m else None


def leer(path, hoja, fila_enc):
    df = pd.read_excel(path, sheet_name=hoja, header=fila_enc, dtype={"DP": str, "DPMP": str, "MPIO": str})
    return df


def agrupar(df, col_mpio):
    df = df[df["ÁREA GEOGRÁFICA"].astype(str).str.strip().str.lower() == "total"]
    df = df[(df["AÑO"] >= DESDE) & (df["AÑO"] <= HASTA)]
    cols = {c: edad_sexo(c) for c in df.columns if edad_sexo(c)}
    largo = []
    for g, a, b, s in GRUPOS:
        sel = [c for c, (sx, ed) in cols.items() if a <= ed <= b and (s is None or sx == s)]
        largo.append(pd.DataFrame({"cod_municipio": df[col_mpio].astype(str).str.zfill(5),
                                   "anio": df["AÑO"].astype(int), "grupo_clave": g,
                                   "poblacion": df[sel].sum(axis=1).round().astype("int64")}))
    hom = [c for c, (sx, _) in cols.items() if sx == "H"]
    muj = [c for c, (sx, _) in cols.items() if sx == "M"]
    tot = pd.DataFrame({"cod_municipio": df[col_mpio].astype(str).str.zfill(5),
                        "anio": df["AÑO"].astype(int),
                        "hombres": df[hom].sum(axis=1).round().astype("int64"),
                        "mujeres": df[muj].sum(axis=1).round().astype("int64")})
    tot["total"] = tot["hombres"] + tot["mujeres"]
    return pd.concat(largo), tot


partes, totales = [], []
f1 = RAW / "PPED-AreaSexoEdadMun-2018-2042_VP.xlsx"
d1 = pd.read_excel(f1, sheet_name="PobMunicipalxÁreaSexoEdad", header=None)
enc = d1.index[d1.iloc[:, 0].astype(str).eq("DP")][0]
d1.columns = [str(a) if str(b) in ("nan", "None") else str(b) for a, b in zip(d1.iloc[enc], d1.iloc[enc + 1])]
d1 = d1.iloc[enc + 2:]
d1["AÑO"] = pd.to_numeric(d1["AÑO"], errors="coerce")
g, t = agrupar(d1, "MPIO")
partes.append(g.assign(fuente="DANE PPED 2018-2042 (act. jul-2025)")); totales.append(t)

if DESDE < 2018:
    f2 = RAW / "DCD-area-sexo-edad-proypoblacion-Mun-2005-2017_VP.xlsx"
    d2 = pd.read_excel(f2, sheet_name=0, header=None)
    enc = d2.index[d2.iloc[:, 0].astype(str).eq("DP")][0]
    d2.columns = d2.iloc[enc].astype(str)
    d2 = d2.iloc[enc + 1:]
    d2["AÑO"] = pd.to_numeric(d2["AÑO"], errors="coerce")
    d2 = d2[d2["AÑO"] < 2018]
    g, t = agrupar(d2, "MPIO")
    partes.append(g.assign(fuente="DANE retroproyección 2005-2017")); totales.append(t)

p = pd.concat(partes).sort_values(["cod_municipio", "anio", "grupo_clave"])
p.to_csv(OUT / "dane_poblacion_municipio_grupo_upc.csv", index=False, encoding="utf-8")
t = pd.concat(totales).sort_values(["cod_municipio", "anio"])
t.to_csv(OUT / "dane_poblacion_municipio_total.csv", index=False, encoding="utf-8")
chk = p.groupby("anio")["poblacion"].sum()
print(p.shape, t.shape)
print(chk.to_string())
