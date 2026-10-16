"""
Procesa los ZIP mensuales de "Cifras de afiliación en salud" (MinSalud) y genera
tablas largas (una fila por periodo y unidad) en data/processed/.

Entrada : data/raw/minsalud_cifras_afiliacion/cifras-afiliacion-salud-AAAA-MM.zip
          data/raw/sispro_cubo_bdua/geografia.csv  (para asignar código DANE cuando
          el libro solo trae nombres, como ocurre de julio a diciembre de 2025)
Salidas :
  minsalud_eps_municipio_regimen_mensual.csv      (EPS x municipio x régimen x mes)
  minsalud_cobertura_municipio_mensual.csv        (municipio x mes, con población DANE)
  minsalud_eps_depto_regimen_quinquenio_sexo.csv  (EPS x depto x régimen x quinquenio x sexo x mes)

Uso: python scripts/01_minsalud_cifras.py
"""
from pathlib import Path
import io
import re
import unicodedata
import zipfile
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
RAW = RAIZ / "data" / "raw" / "minsalud_cifras_afiliacion"
GEO = RAIZ / "data" / "raw" / "sispro_cubo_bdua" / "geografia.csv"
OUT = RAIZ / "data" / "processed"
OUT.mkdir(parents=True, exist_ok=True)


def norm(s) -> str:
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    s = re.sub(r"^\d{5}\s*-\s*", "", s.upper())
    s = re.sub(r"[^A-Z0-9 ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def leer_libro(zpath: Path) -> dict:
    with zipfile.ZipFile(zpath) as z:
        nombre = [n for n in z.namelist() if n.lower().endswith(".xlsx")][0]
        data = z.read(nombre)
    return pd.read_excel(io.BytesIO(data), sheet_name=None, header=None, dtype=object)


def fila_encabezado(df, etiqueta):
    for i in range(6):
        fila = [str(x).strip().lower() for x in df.iloc[i].tolist()]
        if etiqueta in fila:
            return i, fila
    raise ValueError(f"No se encontró el encabezado '{etiqueta}'")


def con_codigo(t):
    return "cod_municipio" in t.columns


# Cruce nombre -> código DANE a partir de la geografía del cubo SISPRO
geo = pd.read_csv(GEO, dtype=str)
geo["k"] = geo["departamento"].map(norm) + "|" + geo["municipio"].map(norm)
cruce = dict(zip(geo["k"], geo["cod_municipio"]))

eps_mpio, cob_mpio, carac = [], [], []
for z in sorted(RAW.glob("cifras-afiliacion-salud-*.zip")):
    periodo = re.search(r"(\d{4}-\d{2})", z.name).group(1)
    libro = leer_libro(z)

    # --- EPS x municipio ---
    df = libro["EPSMunicipio"]
    h, cab = fila_encabezado(df, "eps")
    e = cab.index("eps")
    t = df.iloc[h + 1:].copy()
    out = pd.DataFrame({
        "periodo": periodo,
        "departamento": t.iloc[:, e - 2 if "idmunicipio" not in cab else e - 3],
        "municipio": t.iloc[:, e - 1],
        "eps": t.iloc[:, e],
        "contributivo": t.iloc[:, e + 1],
        "excepcion_especiales": t.iloc[:, e + 3],
        "subsidiado": t.iloc[:, e + 5],
        "total": t.iloc[:, e + 7],
    })
    if "idmunicipio" in cab:
        out.insert(1, "cod_municipio", t.iloc[:, cab.index("idmunicipio")])
    eps_mpio.append(out.dropna(subset=["eps"]))

    # --- Cobertura por municipio ---
    df = libro["CoberturaMunicipio"]
    h, cab = fila_encabezado(df, "contributivo")
    c0 = cab.index("contributivo")
    t = df.iloc[h + 1:].copy()
    nombres = ["contributivo", "subsidiado", "excepcion_especiales", "afiliados", "poblacion_dane",
               "cobertura", "subs_sin_sisben_iv", "subs_pob_especiales_sin_sisben_iv",
               "afil_oficio_sin_sisben_iv", "subs_no_pobre_no_vulnerable"]
    out = pd.DataFrame({"periodo": periodo,
                        "departamento": t.iloc[:, c0 - 3 if "idmunicipio" in cab else c0 - 2],
                        "municipio": t.iloc[:, c0 - 1]})
    for j, n in enumerate(nombres):
        out[n] = t.iloc[:, c0 + j]
    if "idmunicipio" in cab:
        out.insert(1, "cod_municipio", t.iloc[:, cab.index("idmunicipio")])
    cob_mpio.append(out.dropna(subset=["municipio"]))

    # --- Caracterización02: depto x EPS x régimen x quinquenio x sexo ---
    df = libro["Caracterización02"]
    h, cab = fila_encabezado(df, "eps")
    t = df.iloc[h + 1:, :8].copy()
    t.columns = ["departamento", "eps", "regimen", "quinquenio_dane",
                 "femenino", "masculino", "no_reporta", "total"]
    t[["departamento", "eps", "regimen"]] = t[["departamento", "eps", "regimen"]].ffill()
    t = t[t["quinquenio_dane"].astype(str).str.contains("año|Año|mayor|Mayor", regex=True, na=False)]
    t.insert(0, "periodo", periodo)
    carac.append(t)


def asignar_codigo(df):
    """Completa cod_municipio por nombre cuando el libro no lo trae."""
    df = df.copy()
    if "cod_municipio" not in df.columns:
        df["cod_municipio"] = pd.NA
    falta = df["cod_municipio"].isna()
    k = df.loc[falta, "departamento"].map(norm) + "|" + df.loc[falta, "municipio"].map(norm)
    df.loc[falta, "cod_municipio"] = k.map(cruce)
    df["cod_municipio"] = df["cod_municipio"].astype("string").str.zfill(5)
    return df


def enteros(df, cols):
    for c in cols:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype("int64")
    return df


# Cruce adicional: nombres -> código aprendidos de los meses que sí traen código
e = pd.concat(eps_mpio, ignore_index=True)
c = pd.concat(cob_mpio, ignore_index=True)
for d in (e, c):
    if "cod_municipio" in d.columns:
        ok = d.dropna(subset=["cod_municipio"])
        for k, v in zip(ok["departamento"].map(norm) + "|" + ok["municipio"].map(norm),
                        ok["cod_municipio"].astype(str).str.zfill(5)):
            cruce.setdefault(k, v)

e = enteros(asignar_codigo(e), ["contributivo", "subsidiado", "excepcion_especiales", "total"])
e = e[["periodo", "cod_municipio", "departamento", "municipio", "eps",
       "contributivo", "subsidiado", "excepcion_especiales", "total"]]
e.to_csv(OUT / "minsalud_eps_municipio_regimen_mensual.csv", index=False, encoding="utf-8")

c = asignar_codigo(c)
c = enteros(c, ["contributivo", "subsidiado", "excepcion_especiales", "afiliados", "poblacion_dane",
                "subs_sin_sisben_iv", "subs_pob_especiales_sin_sisben_iv",
                "afil_oficio_sin_sisben_iv", "subs_no_pobre_no_vulnerable"])
c["cobertura"] = pd.to_numeric(c["cobertura"], errors="coerce")
c = c[["periodo", "cod_municipio", "departamento", "municipio"] + [x for x in c.columns if x not in
      ("periodo", "cod_municipio", "departamento", "municipio")]]
c.to_csv(OUT / "minsalud_cobertura_municipio_mensual.csv", index=False, encoding="utf-8")

k = enteros(pd.concat(carac, ignore_index=True), ["femenino", "masculino", "no_reporta", "total"])
k.to_csv(OUT / "minsalud_eps_depto_regimen_quinquenio_sexo.csv", index=False, encoding="utf-8")

sin = e[e["cod_municipio"].isna()][["departamento", "municipio"]].drop_duplicates()
print("EPS x municipio :", e.shape, "| filas sin código DANE:", int(e["cod_municipio"].isna().sum()))
if len(sin):
    print(sin.to_string())
print(e.groupby("periodo")["total"].sum().to_string())
print("Cobertura mpio  :", c.shape, "| sin código:", int(c["cod_municipio"].isna().sum()))
print("Caracterización :", k.shape)
print(k.groupby("periodo")["total"].sum().to_string())
