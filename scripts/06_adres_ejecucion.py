"""
Ejecución presupuestal mensual de la ADRES – Unidad de Recursos Administrados (URA),
agosto de 2017 a la fecha, en formato largo.

Entrada : data/raw/adres_ejecucion/adres_ejecucion_AAAA-MM.xls[x]  (un libro por mes,
          publicado en adres.gov.co > Nuestra entidad > Información financiera > URA > Presupuesto)
Salida  : data/processed/adres_ejecucion_rubros_mensual.csv
          columnas: periodo, tipo (ingreso|gasto), codigo, concepto, nivel,
                    presupuesto_definitivo, mes, acumulado, medida
          medida = "recaudo" (ingresos) | "compromiso" | "obligacion" (gastos)

Valores en pesos corrientes, tal como los publica la ADRES. El periodo se toma del encabezado
de la columna "Ingresos desde 01/MM/AAAA" (no del nombre del archivo, que a veces no coincide).
"""
from pathlib import Path
import re
import sys
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
RAW = RAIZ / "data" / "raw" / "adres_ejecucion"
OUT = RAIZ / "data" / "processed"


def norm(s):
    return re.sub(r"\s+", " ", str(s)).strip().upper()


def leer_hoja(path, idx):
    eng = "xlrd" if str(path).endswith(".xls") else "openpyxl"
    return pd.read_excel(path, sheet_name=idx, header=None, engine=eng)


def hojas(path):
    eng = "xlrd" if str(path).endswith(".xls") else "openpyxl"
    return pd.ExcelFile(path, engine=eng).sheet_names


def encabezado(df):
    for i in range(min(25, len(df))):
        fila = [norm(x) for x in df.iloc[i].tolist()]
        if any(x.startswith(("CÓDIGO", "CODIGO")) for x in fila) and any("CONCEPTO" in x for x in fila):
            return i
    return None


def periodo_de(df, h):
    t = " | ".join(norm(x) for x in df.iloc[max(0, h - 3):h + 2].values.ravel())
    m = re.search(r"(?<!ACUMULADOS )(?<!ACUMULADO )(?:INGRESOS?|PRESUPUESTAL)\s+DESDE\s+0?1/(\d{1,2})/(20\d\d)", t)
    return f"{m.group(2)}-{int(m.group(1)):02d}" if m else None


def nivel(cod):
    return str(cod).count("-") + 1


def num(x):
    return pd.to_numeric(x, errors="coerce")


def ingresos(df):
    h = encabezado(df)
    cab = [norm(x) for x in df.iloc[h]]
    per = periodo_de(df, h)
    i_cod = 0
    i_con = 1
    i_def = next(i for i, c in enumerate(cab) if "DEFINITIVO" in c)
    i_mes = next(i for i, c in enumerate(cab) if re.search(r"^INGRESOS? DESDE", c))
    i_acu = next(i for i, c in enumerate(cab) if re.search(r"ACUMULAD", c) and i > i_mes)
    d = df.iloc[h + 1:, [i_cod, i_con, i_def, i_mes, i_acu]].copy()
    d.columns = ["codigo", "concepto", "presupuesto_definitivo", "mes", "acumulado"]
    d = d[d["codigo"].notna() & d["concepto"].notna()]
    d["medida"] = "recaudo"
    return per, d


def gastos(df):
    """Tres bloques: acumulado anterior | mes | acumulado. Medidas: CDP, RP, obligación (u OP/OG)."""
    h = encabezado(df)
    cab = [norm(x) for x in df.iloc[h]]
    fila_med = h + 1 if any(norm(x) in ("RP", "T. RP") for x in df.iloc[h + 1]) else h
    med = [norm(x) for x in df.iloc[fila_med]]
    fila_blq = h if any(re.search(r"EJECUCI", c) for c in cab) else h - 1
    blq = [norm(x) for x in df.iloc[fila_blq]]
    inicios = [i for i, c in enumerate(blq) if c.startswith("EJECUCI")]
    if len(inicios) < 2:
        raise ValueError(f"bloques no reconocidos: {inicios}")
    rangos = list(zip(inicios, inicios[1:] + [len(blq)]))
    if len(rangos) == 2:      # primer mes de la ADRES (agosto de 2017): mes y acumulado coinciden
        i_mes, i_acu = 0, 1
    else:
        i_mes = next(k for k, (a0, _) in enumerate(rangos) if "ACUMUL" not in blq[a0])
        i_acu = max(k for k, (a0, _) in enumerate(rangos) if "ACUMUL" in blq[a0])
    i_def = next((i for i, c in enumerate(cab) if "APROPIACI" in c and "DEFINITIVA" in c),
                 next(i for i, c in enumerate(cab) if "APROPIACI" in c))
    pat = {"compromiso": r"(T\. ?)?RP",
           "obligacion": r"(T\. ?)?(OBLIGACI[ÓO]N|PAGOS-O[PG](AG)?|OG|OP)"}
    out = []
    for medida, rx in pat.items():
        def col(k):
            a0, b0 = rangos[k]
            return next((i for i in range(a0, min(b0, a0 + 4)) if re.fullmatch(rx, med[i])), None)
        m, acu = col(i_mes), col(i_acu)
        if m is None or acu is None:
            continue
        d = df.iloc[max(h, fila_med) + 1:, [0, 1, i_def, m, acu]].copy()
        d.columns = ["codigo", "concepto", "presupuesto_definitivo", "mes", "acumulado"]
        d = d[d["codigo"].notna() & d["concepto"].notna()]
        d["medida"] = medida
        out.append(d)
    return pd.concat(out) if out else pd.DataFrame()


def normalizar_codigo(c):
    c = str(c).strip().replace(" ", "")
    while re.search(r"-0+$", c):
        c = re.sub(r"-0+$", "", c)
    return c


filas, problemas = [], []
for f in sorted(RAW.glob("adres_ejecucion_*.xls*")):
    nombres = hojas(f)
    i_ing = next(i for i, n in enumerate(nombres) if "INGRESO" in n.upper())
    i_gas = next(i for i, n in enumerate(nombres) if "GASTO" in n.upper())
    try:
        per, ing = ingresos(leer_hoja(f, i_ing))
        gas = gastos(leer_hoja(f, i_gas))
    except Exception as e:  # noqa: BLE001
        problemas.append((f.name, repr(e)))
        continue
    for tipo, d in (("ingreso", ing), ("gasto", gas)):
        if d.empty:
            problemas.append((f.name, f"sin {tipo}"))
            continue
        d = d.assign(periodo=per, tipo=tipo)
        filas.append(d)

df = pd.concat(filas, ignore_index=True)
df["codigo_original"] = df["codigo"].astype(str).str.strip()
df["codigo"] = df["codigo_original"].map(normalizar_codigo)
df["concepto"] = df["concepto"].astype(str).str.replace(r"\s+", " ", regex=True).str.strip()
for c in ("presupuesto_definitivo", "mes", "acumulado"):
    df[c] = num(df[c])
df = df[~df["codigo"].str.upper().isin(["NAN", "TOTAL", "", "."]) & ~df["codigo"].str.upper().str.startswith("TOTAL")]
df["nivel"] = df["codigo"].map(nivel)
df = df[["periodo", "tipo", "medida", "codigo", "codigo_original", "nivel", "concepto", "presupuesto_definitivo", "mes", "acumulado"]]
df.to_csv(OUT / "adres_ejecucion_rubros_mensual.csv", index=False, encoding="utf-8")
print(df.shape, df["periodo"].nunique(), df["periodo"].min(), df["periodo"].max())
print(df.groupby(["tipo", "medida"]).size())
for p in problemas:
    print("PROBLEMA", p)
