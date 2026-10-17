"""
Liquidación Mensual de Afiliados (LMA) del régimen subsidiado por municipio y fuente de
financiación, 2020 a la fecha (ADRES, «Informe de Financiación LMA»).

Entrada : data/raw/adres_lma_financiacion/adres_lma_financiacion_AAAA[-MM].xlsx
          Publicado en adres.gov.co → Entidades territoriales → Financiamiento → Informe de
          financiación LMA. Cada libro es acumulado de enero al mes del corte; se usa el de
          diciembre de cada año y el último disponible del año en curso. Hoja «FinalTotal».
Salida  : data/processed/adres_lma_financiacion_municipio_anual.csv
          columnas: anio, meses (12 o los acumulados del año en curso), cod_municipio,
          departamento, municipio, upc_apropiada (A), cajas_compensacion (B),
          cofinanciacion_departamental (C), cofinanciacion_municipal (D),
          aportes_nacion_adres (A-B-C-D), en pesos corrientes.

Notas
  * Es el valor de UPC del subsidiado liquidado a los afiliados de cada municipio y quién lo
    financia. No incluye el contributivo ni los presupuestos máximos.
  * Las filas cuyo código DANE termina en 000 (por ejemplo 91000) son las gobernaciones: afiliados
    de áreas no municipalizadas. Se conservan con su código.
  * Se excluyen las filas de totales departamentales («TOTAL ...»).
"""
from pathlib import Path
import re
import unicodedata
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
RAW = RAIZ / "data" / "raw" / "adres_lma_financiacion"
OUT = RAIZ / "data" / "processed"
MESES = {"ENERO": 1, "FEBRERO": 2, "MARZO": 3, "ABRIL": 4, "MAYO": 5, "JUNIO": 6, "JULIO": 7, "AGOSTO": 8,
         "SEPTIEMBRE": 9, "OCTUBRE": 10, "NOVIEMBRE": 11, "DICIEMBRE": 12}

partes = []
for f in sorted(RAW.glob("adres_lma_financiacion_*.xlsx")):
    d = pd.read_excel(f, sheet_name="FinalTotal", header=None, dtype=str)
    h = d.index[d.apply(lambda r: r.astype(str).str.contains("UPC APROPIADA").any(), axis=1)][0]
    titulo = " ".join(d.iloc[:h].fillna("").astype(str).values.ravel()).upper()
    m = re.search(r"ENERO A (\w+)\s+(?:DE\s+)?(?:AÑO\s+)?(20\d\d)", titulo)
    anio, meses = int(m.group(2)), MESES[m.group(1)]
    cab = [unicodedata.normalize("NFKD", re.sub(r"\s+", " ", str(x)).strip().upper()).encode("ascii", "ignore").decode() for x in d.iloc[h]]
    idx = {k: next(i for i, c in enumerate(cab) if c.startswith(p)) for k, p in [
        ("dane", ("DANE", "CODIGO DANE")), ("departamento", "DEPARTAMENTO"), ("municipio", "MUNICIPIO"),
        ("upc_apropiada", "UPC APROPIADA"), ("cajas_compensacion", "CAJAS"),
        ("cofinanciacion_departamental", "COFINANCIACION DEP"), ("cofinanciacion_municipal", "COFINANCIACION MUN"),
        ("aportes_nacion_adres", "APORTES")]}
    x = d.iloc[h + 1:, list(idx.values())].copy()
    x.columns = list(idx.keys())
    x = x[x["dane"].notna() & x["dane"].astype(str).str.fullmatch(r"\d{4,5}")]
    x["cod_municipio"] = x.pop("dane").str.zfill(5)
    for c in ["upc_apropiada", "cajas_compensacion", "cofinanciacion_departamental", "cofinanciacion_municipal", "aportes_nacion_adres"]:
        x[c] = pd.to_numeric(x[c], errors="coerce").fillna(0).round(0).astype("int64")
    x.insert(0, "meses", meses)
    x.insert(0, "anio", anio)
    x["fuente_archivo"] = f.name
    partes.append(x)

df = pd.concat(partes, ignore_index=True)
df = df[["anio", "meses", "cod_municipio", "departamento", "municipio", "upc_apropiada", "cajas_compensacion",
         "cofinanciacion_departamental", "cofinanciacion_municipal", "aportes_nacion_adres", "fuente_archivo"]]
df.to_csv(OUT / "adres_lma_financiacion_municipio_anual.csv", index=False, encoding="utf-8")
chk = df.assign(dif=df.upc_apropiada - df.cajas_compensacion - df.cofinanciacion_departamental
                - df.cofinanciacion_municipal - df.aportes_nacion_adres)
print(df.groupby(["anio", "meses"])[["upc_apropiada", "aportes_nacion_adres"]].sum().div(1e12).round(2))
print("filas:", len(df), "| máx |A-B-C-D - aportes|:", chk.dif.abs().max())
