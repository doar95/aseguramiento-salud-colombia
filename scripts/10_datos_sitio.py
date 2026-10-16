"""
Genera los JSON compactos que lee el sitio web (docs/data/). No calcula nada nuevo: solo
reorganiza las salidas de los scripts 02-09 para que el navegador las cargue rápido.

Uso: python scripts/10_datos_sitio.py
"""
from pathlib import Path
import json
import math
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
P = RAIZ / "data" / "processed"
REF = RAIZ / "data" / "reference"
OUT = RAIZ / "docs" / "data"
OUT.mkdir(parents=True, exist_ok=True)


def guardar(nombre, obj):
    (OUT / nombre).write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"{nombre}: {(OUT / nombre).stat().st_size / 1024:,.0f} KB")


def num(x, nd=0):
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return None
    return round(float(x), nd) if nd else int(round(float(x)))


# ---------------------------------------------------------------- municipios (atributos)
at = pd.read_csv(P / "municipios_atributos.csv", dtype={"cod_municipio": str, "cod_departamento": str})
mun = {r.cod_municipio: [r.departamento, r.municipio, r.tipo, None if pd.isna(r.ruralidad_2018) else r.ruralidad_2018,
                         None if pd.isna(r.ruralidad_sispro) else r.ruralidad_sispro,
                         num(r.altitud_msnm), None if pd.isna(r.clima) else r.clima]
       for r in at.itertuples()}
guardar("municipios_atributos.json", {"campos": ["departamento", "municipio", "tipo", "ruralidad_2018", "ruralidad_sispro_mtc",
                                                 "altitud_msnm", "clima"], "datos": mun})

# ---------------------------------------------------------------- afiliación por municipio (SISPRO)
s = pd.read_csv(P / "sispro_afiliados_activos_municipio_mensual.csv", dtype={"cod_municipio": str, "periodo": str})
per = sorted(s["periodo"].unique())
frames = [p for p in per if p.endswith("12") and p >= "201312"]
if per[-1] not in frames:
    frames.append(per[-1])
pob = pd.read_csv(P / "dane_poblacion_municipio_total.csv", dtype={"cod_municipio": str})
pobd = {(r.cod_municipio, int(r.anio)): int(r.total) for r in pob.itertuples()}
d = {}
for r in s[s["periodo"].isin(frames)].itertuples():
    i = frames.index(r.periodo)
    v = d.setdefault(r.cod_municipio, [[None] * 4 for _ in frames])
    v[i] = [num(r.contributivo), num(r.subsidiado), num(r.excepcion), num(r.total)]
pobl = {c: [pobd.get((c, int(f[:4]))) for f in frames] for c in d}
guardar("afiliacion_municipio.json", {"periodos": frames, "campos": ["contributivo", "subsidiado", "excepcion", "total"],
                                      "datos": d, "poblacion_dane": pobl,
                                      "fuente": "SISPRO, cubo BDUA (tablero público), afiliados vigentes por municipio de afiliación"})

n = pd.read_csv(P / "sispro_afiliados_activos_nacional_mensual.csv", dtype={"periodo": str})
pn = pob.groupby("anio")["total"].sum().to_dict()
guardar("afiliacion_nacional.json", {"periodo": n["periodo"].tolist(), "contributivo": n["contributivo"].astype(int).tolist(),
                                     "subsidiado": n["subsidiado"].astype(int).tolist(),
                                     "excepcion": n["excepcion"].astype(int).tolist(), "total": n["total"].astype(int).tolist(),
                                     "poblacion_dane_anual": {str(k): int(v) for k, v in pn.items()}})

# ---------------------------------------------------------------- EPS por municipio (MinSalud, último corte)
e = pd.read_csv(P / "minsalud_eps_municipio_regimen_mensual.csv", dtype={"cod_municipio": str})
ult = e["periodo"].max()
e = e[e["periodo"] == ult]
eps = {}
for r in e.itertuples():
    eps.setdefault(r.cod_municipio, []).append([r.eps, num(r.contributivo), num(r.subsidiado), num(r.excepcion_especiales)])
for c in eps:
    eps[c].sort(key=lambda x: -(x[1] + x[2] + x[3]))
guardar("eps_municipio.json", {"periodo": ult, "campos": ["eps", "contributivo", "subsidiado", "excepcion"], "datos": eps,
                               "fuente": "MinSalud, Cifras de aseguramiento en salud"})

# ---------------------------------------------------------------- edad por municipio (ADRES, datos abiertos)
fs = sorted(P.glob("adres_bdua_eps_municipio_sexo_grupo_upc_*.csv.gz"))
a = pd.read_csv(fs[-1], dtype={"cod_municipio": str})
corte = a["corte"].iloc[0]
grupos = ["<1", "1-4", "5-14", "15-18H", "15-18M", "19-44H", "19-44M", "45-49", "50-54", "55-59", "60-64", "65-69", "70-74", "75+"]
g = a.groupby(["cod_municipio", "regimen", "grupo_clave"])["afiliados"].sum()
edad = {}
for (c, reg, gk), v in g.items():
    x = edad.setdefault(c, {}).setdefault(reg[0].upper(), [0] * len(grupos))
    x[grupos.index(gk)] = int(v)
guardar("edad_municipio.json", {"corte": corte, "grupos": grupos, "datos": edad,
                                "fuente": "ADRES, BDUA en datos.gov.co (tq4m-hmg2 y d7a5-cnra)"})

# ---------------------------------------------------------------- UPC
b = pd.read_csv(P / "upc_valor_base_anual.csv")
fu = json.loads((RAIZ / "docs" / "fuentes.json").read_text(encoding="utf-8"))
urls = {n["vigencia_upc"]: n["url"] for n in fu["normas"] if n.get("vigencia_upc")}
ec = pd.read_csv(P / "upc_estructura_costo_grupo_etario.csv")
pond = {}
for r in ec.itertuples():
    pond.setdefault(str(r.vigencia), {}).setdefault(r.regimen[0].upper(), {})[r.grupo_clave] = r.estructura_costo
pz = pd.read_csv(P / "upc_primas_zona.csv")
mz = pd.read_csv(P / "upc_municipio_zona.csv", dtype={"cod_municipio": str})
zonas = {}
for r in mz.itertuples():
    zonas.setdefault(str(r.vigencia), {}).setdefault(r.regimen, {})[r.cod_municipio] = r.zona
verif = {}
for r in mz.itertuples():
    if not r.verificacion.startswith(("código y nombre", "código del anexo", "ciudad nombrada", "departamento Archipi",
                                      "código leído por OCR")):
        verif.setdefault(str(r.vigencia), {}).setdefault(r.regimen, {})[r.cod_municipio] = r.verificacion
pe = pd.read_csv(P / "upc_prima_etaria_eps.csv")
guardar("upc.json", {
    "base": [{"vigencia": int(r.vigencia), "resolucion": r.resolucion, "fecha": r.fecha_expedicion, "upc_c": r.upc_c_anual,
              "upc_s": r.upc_s_anual, "razon_s_c": r.razon_s_c, "url": urls.get(int(r.vigencia))} for r in b.itertuples()],
    "ponderadores": pond, "grupos": grupos,
    "primas": pz.where(pz.notna(), None).to_dict(orient="records"),
    "zonas_municipio": zonas, "verificacion_no_directa": verif,
    "prima_etaria_eps": pe.to_dict(orient="records")})

# ---------------------------------------------------------------- finanzas ADRES
f = pd.read_csv(P / "adres_ejecucion_categorias_mensual.csv")
f["anio"] = f["periodo"].str[:4]
fin = {}
for (tipo, med), g in f.groupby(["tipo", "medida"]):
    k = f"{tipo}_{med}"
    a1 = g.groupby(["anio", "categoria"])[["valor_mes_corriente", "valor_mes_constante"]].sum().reset_index()
    fin[k] = {"anual": [[r.anio, r.categoria, round(r.valor_mes_corriente / 1e9, 1), round(r.valor_mes_constante / 1e9, 1)]
                        for r in a1.itertuples()]}
    sub = g.groupby(["anio", "categoria", "subcategoria"])[["valor_mes_corriente", "valor_mes_constante"]].sum().reset_index()
    fin[k]["subcategorias"] = [[r.anio, r.categoria, r.subcategoria, round(r.valor_mes_corriente / 1e9, 1),
                                round(r.valor_mes_constante / 1e9, 1)] for r in sub.itertuples()]
    if tipo == "gasto":
        m1 = g.groupby(["periodo", "grupo_empalme"])[["valor_mes_corriente", "valor_mes_constante"]].sum().reset_index()
        fin[k]["mensual_empalme"] = [[r.periodo, r.grupo_empalme, round(r.valor_mes_corriente / 1e9, 1),
                                      round(r.valor_mes_constante / 1e9, 1)] for r in m1.itertuples()]
ipc = pd.read_csv(P / "ipc_dane_mensual.csv")
cl = pd.read_csv(REF / "adres_clasificacion_rubros.csv")
just = cl.drop_duplicates("categoria")[["tipo", "categoria", "grupo_empalme", "justificacion"]].fillna("").to_dict(orient="records")
guardar("finanzas.json", {"unidad": "miles de millones de pesos", "base_constantes": "septiembre de 2026 (IPC DANE)",
                          "periodos": [f["periodo"].min(), f["periodo"].max()], "datos": fin, "justificacion": just,
                          "ipc": ipc.values.tolist()})

# ---------------------------------------------------------------- Corte Constitucional
c = pd.read_csv(REF / "corte_constitucional_autos.csv")
guardar("corte.json", c.to_dict(orient="records"))

meta = {"generado": pd.Timestamp.now(tz="America/Bogota").strftime("%Y-%m-%d"),
        "sispro_ultimo_periodo": per[-1], "minsalud_ultimo_periodo": ult, "adres_bdua_corte": corte,
        "adres_ejecucion": [f["periodo"].min(), f["periodo"].max()]}
guardar("meta.json", meta)
