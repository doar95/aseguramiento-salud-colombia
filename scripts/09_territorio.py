"""
Atributos territoriales por municipio y geometría simplificada para el mapa.

Entradas
  data/raw/dane/DIVIPOLA_Municipios.xlsx            DANE, DIVIPOLA (junio de 2026), hoja "Municipios"
  data/raw/dane/MGN2024_MPIO_POLITICO.zip           DANE, Marco Geoestadístico Nacional 2024 (no se versiona: 100+ MB)
  data/raw/base_interna/Altitud_municipios_Colombia.xlsx      altitud y clima (ver docs/fuentes.md)
  data/raw/base_interna/Clasificacion_de_ruralidad_2018.xlsx  categoría de ruralidad 2018 (base interna)
  data/raw/sispro_cubo_bdua/geografia.csv           categoría de ruralidad que trae el cubo BDUA de SISPRO
Salidas
  data/processed/municipios_atributos.csv
  docs/data/municipios.geojson   (solo si existe el zip del MGN; topología simplificada, ~1,4 MB)
"""
from pathlib import Path
import zipfile
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
RAW = RAIZ / "data" / "raw"
OUT = RAIZ / "data" / "processed"

dv = pd.read_excel(RAW / "dane" / "DIVIPOLA_Municipios.xlsx", sheet_name="Municipios", header=None, dtype=str)
h = dv.index[dv.iloc[:, 0].astype(str).str.strip().eq("Código")][0]
dv = dv.iloc[h + 1:, :8]
dv.columns = ["cod_departamento", "departamento", "cod_municipio", "municipio", "tipo", "longitud", "latitud", "nota"]
dv = dv.dropna(subset=["cod_municipio"])
dv["cod_municipio"] = dv["cod_municipio"].str.strip().str.zfill(5)
dv["tipo"] = dv["tipo"].str.replace(r"\s+", " ", regex=True).str.strip()

alt = pd.read_excel(RAW / "base_interna" / "Altitud_municipios_Colombia.xlsx", header=4, dtype=str)
alt = alt.rename(columns={"DPMP": "cod_municipio", "ALTITUD (MSNM)": "altitud_msnm", "CLIMA": "clima"})
alt["cod_municipio"] = alt["cod_municipio"].str.zfill(5)
alt["altitud_msnm"] = pd.to_numeric(alt["altitud_msnm"], errors="coerce")

rur = pd.read_excel(RAW / "base_interna" / "Clasificacion_de_ruralidad_2018.xlsx", dtype=str)
rur = rur.rename(columns={"Código DANE": "cod_municipio", "Clasificación de Ruralidad 2018": "ruralidad_2018"})
rur["cod_municipio"] = rur["cod_municipio"].str.zfill(5)

geo = pd.read_csv(RAW / "sispro_cubo_bdua" / "geografia.csv", dtype=str)
geo = geo.rename(columns={"categoria_ruralidad": "ruralidad_sispro"})

m = (dv[["cod_departamento", "departamento", "cod_municipio", "municipio", "tipo", "longitud", "latitud"]]
     .merge(alt[["cod_municipio", "altitud_msnm", "clima"]], on="cod_municipio", how="left")
     .merge(rur[["cod_municipio", "ruralidad_2018"]], on="cod_municipio", how="left")
     .merge(geo[["cod_municipio", "ruralidad_sispro"]], on="cod_municipio", how="left"))
bins = [-1, 1000, 2000, 3000, 10000]
m["altitud_rango"] = pd.cut(m["altitud_msnm"], bins=bins, labels=["0-1.000", "1.000-2.000", "2.000-3.000", "3.000+"]).astype(str)
m.to_csv(OUT / "municipios_atributos.csv", index=False, encoding="utf-8")
print(m.shape)
print("sin altitud:", m["altitud_msnm"].isna().sum(), "| sin ruralidad 2018:", m["ruralidad_2018"].isna().sum())

zp = RAW / "dane" / "MGN2024_MPIO_POLITICO.zip"
if zp.exists():
    import geopandas as gpd
    import topojson as tp
    tmp = RAIZ / "data" / "raw" / "dane" / "_mgn"
    with zipfile.ZipFile(zp) as z:
        z.extractall(tmp)
    shp = next(tmp.rglob("*MPIO*.shp"))
    g = gpd.read_file(shp).to_crs(4326)
    col = next(c for c in g.columns if c.upper() in ("MPIO_CDPMP", "MPIO_CCNCT", "COD_MPIO"))
    g = g.rename(columns={col: "cod"})[["cod", "geometry"]]
    g["cod"] = g["cod"].astype(str).str.zfill(5)
    g = g.merge(m[["cod_municipio", "departamento", "municipio"]].rename(columns={"cod_municipio": "cod", "departamento": "depto", "municipio": "mpio"}), on="cod", how="left")
    g["area_km2"] = g.to_crs(9377).area.div(1e6).round(1)
    topo = tp.Topology(g, prequantize=1e6, toposimplify=0.004)
    (RAIZ / "docs" / "data").mkdir(parents=True, exist_ok=True)
    (RAIZ / "docs" / "data" / "municipios.geojson").write_text(topo.to_geojson())
    print("geometría:", len(g))
