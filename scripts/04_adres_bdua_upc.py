"""
Afiliados por EPS (código), municipio, sexo, grupo etario UPC y zona, a partir de los
conjuntos de datos abiertos de la ADRES en datos.gov.co, y un ejercicio ILUSTRATIVO de
UPC teórica (afiliados x estructura de costo x UPC base de la vigencia).

Entradas:
  data/raw/adres_datos_abiertos/corte-AAAA-MM/bdua_{contributivo,subsidiado}_agregado.csv.gz
  data/raw/sispro_cubo_bdua/geografia.csv           (cruce nombre de municipio -> código DANE)
  data/processed/upc_estructura_costo_grupo_etario.csv
Salidas:
  adres_bdua_eps_municipio_sexo_grupo_upc_<corte>.csv
  adres_upc_teorica_eps_municipio_<corte>.csv  (ILUSTRATIVO, ver advertencias)

ADVERTENCIAS sobre la UPC teórica:
  * Aplica la UPC de la zona del municipio de afiliación (dispersión, ciudades, San Andrés,
    Guainía) según data/processed/upc_municipio_zona.csv (scripts/08_upc_zonas.py). El
    municipio de la BDUA es el de afiliación, no necesariamente el de residencia o atención.
  * No aplica la prima por concentración de riesgo etario, la UPC diferencial indígena,
    ni los días efectivamente compensados/liquidados.
  * La BDUA publicada es una foto del corte; la compensación (contributivo) y la LMA
    (subsidiado) se liquidan con reglas propias (días, novedades, restituciones).
  Sirve para comparar EPS y municipios en una misma escala, no para estimar giros reales.

Uso: python scripts/04_adres_bdua_upc.py 2026-09
"""
from pathlib import Path
import sys
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
CORTE = sys.argv[1] if len(sys.argv) > 1 else "2026-09"
RAW = RAIZ / "data" / "raw" / "adres_datos_abiertos" / f"corte-{CORTE}"
OUT = RAIZ / "data" / "processed"
VIGENCIA = int(CORTE[:4])


sys.path.insert(0, str(Path(__file__).resolve().parent))
from comun import cargar_cruce, codigo_dane  # noqa: E402

CRUCE = cargar_cruce()


def grupo_upc(edad, sexo):
    e = str(edad).strip()
    h = sexo.lower().startswith("m")
    return {"< 1": "<1", "1 a 5": "1-4", "5 a 15": "5-14",
            "15 a 19": "15-18H" if h else "15-18M", "19 a 45": "19-44H" if h else "19-44M",
            "45 a 50": "45-49", "50 a 55": "50-54", "55 a 60": "55-59", "60 a 65": "60-64",
            "65 a 70": "65-69", "70 a 75": "70-74", "> 75": "75+"}.get(e)


partes = []
for reg in ("contributivo", "subsidiado"):
    d = pd.read_csv(RAW / f"bdua_{reg}_agregado.csv.gz", dtype=str)
    d["afiliados"] = d["afiliados"].astype(int)
    partes.append(d)
d = pd.concat(partes, ignore_index=True)

pares = d[["dpr_nombre", "mnc_nombre"]].drop_duplicates()
pares["cod_municipio"] = [codigo_dane(CRUCE, a, b) for a, b in zip(pares["dpr_nombre"], pares["mnc_nombre"])]
d = d.merge(pares, on=["dpr_nombre", "mnc_nombre"], how="left")
d["grupo_clave"] = [grupo_upc(e, s) for e, s in zip(d["tps_grp_etr_id"], d["tps_gnr_nombre"])]
d["regimen"] = d["tps_rgm_nombre"].str.lower()

t = (d.groupby(["regimen", "ent_id", "ent_nombre", "cod_municipio", "dpr_nombre", "mnc_nombre",
                "tps_gnr_nombre", "grupo_clave", "zns_nombre", "tps_est_afl_nombre"], dropna=False)
       ["afiliados"].sum().reset_index()
       .rename(columns={"ent_id": "cod_eps", "ent_nombre": "eps", "dpr_nombre": "departamento",
                        "mnc_nombre": "municipio", "tps_gnr_nombre": "sexo",
                        "zns_nombre": "zona_afiliacion", "tps_est_afl_nombre": "estado"}))
t.insert(0, "corte", CORTE)
t.to_csv(OUT / f"adres_bdua_eps_municipio_sexo_grupo_upc_{CORTE}.csv.gz", index=False, encoding="utf-8")

# --- UPC teórica ilustrativa (con prima de zona) ---
p = pd.read_csv(OUT / "upc_estructura_costo_grupo_etario.csv")
if VIGENCIA not in set(p["vigencia"]):
    print(f"La resolución de UPC de {VIGENCIA} aún no está en el repositorio: se guarda la afiliación "
          "y se omite la UPC teórica de este corte.")
    sys.exit(0)
p = p[p["vigencia"] == VIGENCIA][["regimen", "grupo_clave", "estructura_costo", "valor_anual_zona_normal"]]
u = t.merge(p, on=["regimen", "grupo_clave"], how="left")
# factor de zona = UPC de la zona / UPC base (variante general de la resolución de la vigencia)
pz = pd.read_csv(OUT / "upc_primas_zona.csv")
pz = pz[(pz["vigencia"] == VIGENCIA) & (pz["variante"] == "general")]
fz = {(r.regimen, r.zona): 1 + r.prima for r in pz.itertuples()}
mz = pd.read_csv(OUT / "upc_municipio_zona.csv", dtype={"cod_municipio": str})
mz = mz[mz["vigencia"] == VIGENCIA]
zona = {(("contributivo" if r.regimen == "C" else "subsidiado"), r.cod_municipio): r.zona for r in mz.itertuples()}
u["zona_upc"] = [zona.get((a, b), "resto_pais") for a, b in zip(u["regimen"], u["cod_municipio"])]
u["factor_zona"] = [fz.get(("C" if a == "contributivo" else "S", z), 1.0) for a, z in zip(u["regimen"], u["zona_upc"])]
u["upc_teorica_anual"] = u["afiliados"] * u["valor_anual_zona_normal"] * u["factor_zona"]
r = (u.groupby(["corte", "regimen", "cod_eps", "eps", "cod_municipio", "departamento", "municipio", "zona_upc"], dropna=False)
       .agg(afiliados=("afiliados", "sum"),
            suma_ponderada=("estructura_costo", lambda s: (s * u.loc[s.index, "afiliados"]).sum()),
            upc_teorica_anual=("upc_teorica_anual", "sum"))
       .reset_index())
r["ponderador_promedio"] = (r["suma_ponderada"] / r["afiliados"]).round(4)
r = r.drop(columns="suma_ponderada")
r.to_csv(OUT / f"adres_upc_teorica_eps_municipio_{CORTE}.csv", index=False, encoding="utf-8")

sin = pares[pares["cod_municipio"].isna()]
print("Afiliados por régimen:", t.groupby("regimen")["afiliados"].sum().to_dict())
print("Pares depto-municipio sin código DANE:", len(sin), "| afiliados:",
      int(d.loc[d["cod_municipio"].isna(), "afiliados"].sum()))
if len(sin):
    print(sin.head(40).to_string(index=False))
print("Grupos sin mapear:", d.loc[d["grupo_clave"].isna(), "tps_grp_etr_id"].unique())
print(r.groupby("regimen")[["afiliados", "upc_teorica_anual"]].sum())
