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


# ================================================================ páginas adicionales (v1.1)
# ---------------------------------------------------------------- departamentos: serie mensual SISPRO
s["dep"] = s["cod_municipio"].str[:2]
dm = s.groupby(["dep", "periodo"])[["contributivo", "subsidiado", "excepcion", "total"]].sum().reset_index()
deps = {c[:2]: a[0] for c, a in mun.items()}
pobdep = pob.assign(dep=pob["cod_municipio"].str[:2]).groupby(["dep", "anio"])["total"].sum()
guardar("departamentos.json", {
    "periodos": per, "nombres": deps,
    "datos": {d: {k: g.set_index("periodo").reindex(per)[k].fillna(0).astype(int).tolist()
                  for k in ["contributivo", "subsidiado", "excepcion", "total"]} for d, g in dm.groupby("dep")},
    "poblacion_dane": {d: {str(a): int(v) for (dd, a), v in pobdep.items() if dd == d} for d in deps}})

# ---------------------------------------------------------------- EPS: serie mensual por departamento
em = pd.read_csv(P / "minsalud_eps_municipio_regimen_mensual.csv", dtype={"cod_municipio": str})
em["dep"] = em["cod_municipio"].str[:2]
em = em.groupby(["periodo", "eps", "dep"])[["contributivo", "subsidiado", "excepcion_especiales"]].sum().reset_index()
pb = pd.read_csv(RAIZ / "data" / "raw" / "minsalud_tablero_powerbi" / "eps_municipio_regimen_cod_eps.csv", dtype=str)
cat = pd.read_csv(RAIZ / "data" / "raw" / "minsalud_tablero_powerbi" / "catalogo_eps.csv", dtype=str)
pb = pb[pb["fecha_corte"] == "2024-12-01"].merge(cat[["cod_eps", "nombre_corto_eps"]], on="cod_eps", how="left")
pb["afiliados"] = pb["afiliados"].astype(int)
pb["dep"] = pb["cod_municipio"].str[:2]
pb["col"] = pb["regimen"].map({"CONTRIBUTIVO": "contributivo", "SUBSIDIADO": "subsidiado"}).fillna("excepcion_especiales")
pbw = pb.pivot_table(index=["nombre_corto_eps", "dep"], columns="col", values="afiliados", aggfunc="sum", fill_value=0).reset_index()
pbw = pbw.rename(columns={"nombre_corto_eps": "eps"}).assign(periodo="2024-12")
for c in ["contributivo", "subsidiado", "excepcion_especiales"]:
    if c not in pbw:
        pbw[c] = 0
em = pd.concat([pbw[em.columns], em], ignore_index=True)
pers = sorted(em["periodo"].unique())
eps_ser = {}
for (e, d), g in em.groupby(["eps", "dep"]):
    g = g.set_index("periodo").reindex(pers).fillna(0)
    eps_ser.setdefault(e, {})[d] = [g["contributivo"].astype(int).tolist(), g["subsidiado"].astype(int).tolist(),
                                    g["excepcion_especiales"].astype(int).tolist()]
med = pd.read_csv(REF / "eps_medidas_supersalud.csv").fillna("")
guardar("eps_series.json", {"periodos": pers, "datos": eps_ser, "nombres_dep": deps,
                            "nota": "2024-12: tablero Power BI de MinSalud (por código, unido al catálogo); 2025-07 en adelante: Cifras de aseguramiento (MinSalud).",
                            "medidas": med.to_dict(orient="records")})

# ---------------------------------------------------------------- EPS: edad (quinquenio) y sexo, último corte
q = pd.read_csv(P / "minsalud_eps_depto_regimen_quinquenio_sexo.csv")
q = q[q["periodo"] == q["periodo"].max()]
qs = sorted(q["quinquenio_dane"].unique(), key=lambda x: int("".join(ch for ch in x.split(" a ")[0] if ch.isdigit()) or 0))
pir = {}
for (e, dn, r), g in q.groupby(["eps", "departamento", "regimen"]):
    g = g.set_index("quinquenio_dane").reindex(qs).fillna(0)
    pir.setdefault(e, {}).setdefault(dn, {})[r[0]] = [g["femenino"].astype(int).tolist(), g["masculino"].astype(int).tolist()]
guardar("eps_edad.json", {"periodo": q["periodo"].iloc[0], "quinquenios": qs, "datos": pir})

# ---------------------------------------------------------------- LMA por municipio
lm = pd.read_csv(P / "adres_lma_financiacion_municipio_anual.csv", dtype={"cod_municipio": str})
anios = sorted(lm["anio"].unique().tolist())
lma = {}
for r in lm.itertuples():
    v = lma.setdefault(r.cod_municipio, [None] * len(anios))
    v[anios.index(r.anio)] = [r.upc_apropiada, r.cajas_compensacion, r.cofinanciacion_departamental,
                              r.cofinanciacion_municipal, r.aportes_nacion_adres]
meses = lm.groupby("anio")["meses"].first().to_dict()
guardar("lma.json", {"anios": anios, "meses": {str(k): int(v) for k, v in meses.items()},
                     "campos": ["upc_apropiada", "cajas_compensacion", "cofinanciacion_departamental",
                                "cofinanciacion_municipal", "aportes_nacion_adres"],
                     "datos": lma, "fuente": "ADRES, Informe de Financiación LMA (Entidades territoriales → Financiamiento)"})

# ---------------------------------------------------------------- EPS intervenidas por municipio y mes
# Regla: un mes cuenta como intervenido si la medida estuvo vigente algún día de ese mes.
# Coosalud se guarda aparte porque su situación está en disputa (ver eps_medidas_supersalud.csv).
import calendar
emm = pd.read_csv(P / "minsalud_eps_municipio_regimen_mensual.csv", dtype={"cod_municipio": str})
emm = emm[["periodo", "cod_municipio", "eps", "contributivo", "subsidiado"]]
pbm = pb.groupby(["cod_municipio", "nombre_corto_eps", "col"])["afiliados"].sum().unstack(fill_value=0).reset_index()
pbm = pbm.rename(columns={"nombre_corto_eps": "eps"}).assign(periodo="2024-12")
for c in ["contributivo", "subsidiado"]:
    if c not in pbm:
        pbm[c] = 0
emm = pd.concat([pbm[emm.columns], emm], ignore_index=True)
emm["cs"] = emm["contributivo"] + emm["subsidiado"]


def intervenida(eps, per):
    m = med[med["eps_minsalud"] == eps]
    if m.empty:
        return False
    m = m.iloc[0]
    y, mo = int(per[:4]), int(per[5:7])
    ini, fin = f"{per}-01", f"{per}-{calendar.monthrange(y, mo)[1]:02d}"
    return m["fecha_inicio"] <= fin and (not m["fecha_fin"] or m["fecha_fin"] >= ini)


pairs = emm[["eps", "periodo"]].drop_duplicates()
pairs["iv"] = [intervenida(e, p) for e, p in zip(pairs["eps"], pairs["periodo"])]
emm = emm.merge(pairs, on=["eps", "periodo"])
emm["coos"] = (emm["eps"] == "COOSALUD EPS") & emm["iv"]
emm["iv_sin"] = emm["iv"] & ~emm["coos"]
agg = emm.groupby(["cod_municipio", "periodo"]).apply(
    lambda g: pd.Series({"t": g["cs"].sum(), "i": g.loc[g["iv_sin"], "cs"].sum(), "c": g.loc[g["coos"], "cs"].sum()}), include_groups=False).reset_index()
pi = sorted(agg["periodo"].unique())
iv_d = {}
for cod, g in agg.groupby("cod_municipio"):
    g = g.set_index("periodo").reindex(pi).fillna(0)
    iv_d[cod] = [[int(a), int(b), int(c)] for a, b, c in zip(g["t"], g["i"], g["c"])]
nac = agg.groupby("periodo")[["t", "i", "c"]].sum().reindex(pi)
guardar("intervenidas.json", {"periodos": pi, "campos": ["afiliados_c_s", "en_intervenidas_sin_coosalud", "en_coosalud_intervenida"],
                              "datos": iv_d, "nacional": nac.astype(int).values.tolist(),
                              "nota": "Contributivo + subsidiado. Fuente: MinSalud; medidas en data/reference/eps_medidas_supersalud.csv."})
print(nac.assign(pct=lambda x: (x.i + x.c) / x.t).round(3).to_string())

# ---------------------------------------------------------------- protección laboral (contributivo), corte ADRES
pr = a[a["regimen"] == "contributivo"].copy()
pr["prot"] = pr["estado"].astype(str).str.contains("Protecci", case=False)
pg = pr.groupby(["cod_municipio", "prot"])["afiliados"].sum().unstack(fill_value=0)
guardar("proteccion_laboral.json", {"corte": corte, "campos": ["proteccion_laboral", "contributivo_total"],
                                    "datos": {c: [int(r.get(True, 0)), int(r.get(True, 0) + r.get(False, 0))] for c, r in pg.iterrows()},
                                    "fuente": "ADRES, BDUA régimen contributivo (datos.gov.co, tq4m-hmg2), estado «Protección Laboral»"})
