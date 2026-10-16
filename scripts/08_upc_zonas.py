"""
UPC por zona y municipio, vigencias 2013-2026, a partir del texto de cada resolución anual.

Entradas
  normativa/upc/texto/upc_vigencia-AAAA_*.txt     texto de cada resolución (pdftotext; OCR tesseract
                                                   para las escaneadas, archivos *_psm4.txt)
  data/reference/upc_anexos_ocr/AAAA.txt         códigos DANE leídos por OCR de la columna "Código"
                                                   de los anexos escaneados (2014, 2015, 2018, 2021)
  data/raw/sispro_cubo_bdua/geografia.csv        nombres y códigos de municipio (incluye códigos históricos)
  data/processed/upc_valor_base_anual.csv        UPC base (salida de 03_upc_parametros.py)

Salidas (data/processed/)
  upc_valores_por_articulo.csv   cada tabla etaria publicada en la resolución -> UPC anual implícita
                                 (= valor del grupo "menores de un año" / su ponderador) y su razón
                                 frente a la UPC base. Es la prueba de que cada prima está bien leída.
  upc_primas_zona.csv            vigencia x régimen x variante x zona: prima y UPC anual.
  upc_municipio_zona.csv         vigencia x régimen x municipio -> zona (solo municipios con prima;
                                 el resto del país recibe la UPC base).
  upc_prima_etaria_eps.csv       prima por concentración de riesgo etario reconocida a EPS específicas.

Reglas de verificación (no se imputa nada en silencio):
  * Los anexos de dispersión se leen por código y nombre; si el código impreso no existe se busca
    el nombre dentro del departamento. Columna `verificacion` dice cómo se obtuvo cada fila.
  * En años escaneados, las filas que el OCR no logró leer se incluyen SOLO si: (a) el anexo tiene
    el mismo número total de filas que la lista de las vigencias vecinas, (b) todas las filas leídas
    coinciden con esa lista y (c) el código figura en la vigencia anterior y en la siguiente.
    Se marcan "fila no legible por OCR; inferida (...)". Las que se revisaron a ojo sobre la imagen
    se marcan "verificada visualmente".
  * 2013 no tiene anexo: la dispersión se define por departamentos más "la región de Urabá" y se
    exceptúan Arauca, Florencia y Yopal "con sus respectivas áreas de influencia" (que la resolución
    no delimita). Se marca así.
"""
from pathlib import Path
import difflib
import glob
import re
import unicodedata
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
TXT = RAIZ / "normativa" / "upc" / "texto"
OCR = RAIZ / "data" / "reference" / "upc_anexos_ocr"
OUT = RAIZ / "data" / "processed"
GEO = RAIZ / "data" / "raw" / "sispro_cubo_bdua" / "geografia.csv"

BASE = pd.read_csv(OUT / "upc_valor_base_anual.csv")
BASE = {**{(int(r.vigencia), "C"): float(r.upc_c_anual) for r in BASE.itertuples()},
        **{(int(r.vigencia), "S"): float(r.upc_s_anual) for r in BASE.itertuples()}}

RES = {2013: "Resolución 4480 de 2012", 2014: "Resolución 5522 de 2013", 2015: "Resolución 5925 de 2014",
       2016: "Resolución 5593 de 2015", 2017: "Resolución 6411 de 2016", 2018: "Resolución 5268 de 2017",
       2019: "Resolución 5858 de 2018", 2020: "Resolución 3513 de 2019", 2021: "Resolución 2503 de 2020",
       2022: "Resolución 2381 de 2021", 2023: "Resolución 2809 de 2022", 2024: "Resolución 2364 de 2023",
       2025: "Resolución 2717 de 2024", 2026: "Resolución 2764 de 2025"}


def norm(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().upper()
    return re.sub(r"\s+", " ", re.sub(r"[^A-Z0-9 ]", " ", s)).strip()


def textos(y):
    """texto plano y, si existe, la versión OCR psm4 (se usan ambas)."""
    fs = sorted(glob.glob(str(TXT / f"upc_vigencia-{y}_*.txt")))
    return [re.sub(r"\s+", " ", open(f, encoding="utf-8", errors="ignore").read()) for f in fs]


def pesos(s):
    """'2.218.712,40' | '$5,022,752.19' | '1.948.104' -> float"""
    s = s.strip().lstrip("$").strip()
    m = re.fullmatch(r"(\d{1,3}(?:[.,]\d{3})+)(?:[.,](\d{2}))?", s)
    if not m:
        return None
    return float(re.sub(r"[.,]", "", m.group(1)) + "." + (m.group(2) or "00"))


# ----------------------------------------------------------------------------------------------
# 1. Tablas etarias publicadas -> UPC implícita por artículo
# ----------------------------------------------------------------------------------------------
RX_TABLA = re.compile(r"Menores de (?:un|1) a[ñn]o[\s|_]*(\d[,.]\d{4})[\s|_]*\$?\s?(\d{1,3}(?:[.,]\d{3})+(?:[.,]\d{2})?)(?!\d)", re.I)
RX_ART = re.compile(r"(?:ART[ÍI]CULO|Art[íi]culo|Articulo)\s*(?:(\d{1,2}|[A-ZÉÍÓÚ]+(?: [A-ZÉÍÓÚ]+)?)\s*[.°º:-]|(?=Unidad de [Pp]ago))")


def clasificar(desc, reg):
    d = desc.lower()
    variante = "general"
    if "nuevas inclusiones" in d or "resolución 2292" in d:
        variante = "con_inclusiones_res_2292_2021"
    if re.search(r"ind[íi]gena|epsi|upcdi|upcd1|4[,.]81 ?%|incremento del ?4|(sobre|al) (el )?valor fijado (para la (upc|unidad de pago por capitaci[óo]n) )?en el art[íi]culo 1[4-7]", d):
        variante = "indigena_epsi" if variante == "general" else variante + "+indigena_epsi"
    if "piloto" in d:
        return "piloto_igualacion_prima_pura", "ciudades_piloto"
    if "guain" in d:
        zona = "guainia"
    elif "alejada" in d or "archipi" in d:
        zona = "san_andres"
    elif "dispersi" in d:
        zona = "dispersion"
    elif "ciudades" in d:
        zona = "ciudades"
    elif re.search(r"promoci[óo]n|prevenci", d[:200]):
        zona = "otro"
    else:
        zona = "resto_pais"
    return variante, zona


def valores_por_articulo():
    filas = []
    for y in range(2013, 2027):
        vistos = set()
        for t in textos(y):
            arts = [(m.start(), m.group(0)) for m in RX_ART.finditer(t)]
            for m in RX_TABLA.finditer(t):
                pond = float(m.group(1).replace(",", "."))
                v = pesos(m.group(2))
                if not v or pond not in (2.9679, 2.9966, 2.7654):
                    continue
                reg = "S" if pond == 2.7654 else "C"
                upc = round(v / pond, 2)
                a0, art = max([(a, n) for a, n in arts if a < m.start()] or [(0, "")])
                desc = t[a0 + len(art): a0 + len(art) + 260].strip()
                if desc.lower().startswith(("las licencias", "fijar el valor que se reconoce")):
                    continue   # artículos sin tabla propia (el bloque pertenece a otro)
                variante, zona = clasificar(desc, reg)
                if y == 2022 and zona != "otro" and "con_inclusiones" not in variante and re.search(r"art[íi]culo (8|25)\b", desc, re.I):
                    variante = "con_inclusiones_res_2292_2021" + ("+indigena_epsi" if "indigena" in variante else "")
                if "EPSI03" in desc.replace(" ", "").upper() or "EPS103" in desc.upper():
                    variante = "indigena_epsi03"
                b = BASE[(y, reg)]
                clave = (reg, variante, zona, round(upc / b, 3))
                if clave in vistos:
                    continue
                vistos.add(clave)
                filas.append(dict(vigencia=y, regimen=reg, variante=variante, zona=zona,
                                  articulo=re.sub(r"\s+", " ", art).strip(" .:-"), upc_anual_implicita=upc,
                                  razon_vs_base=round(upc / b, 4), descripcion=desc[:200]))
    return pd.DataFrame(filas)


# ----------------------------------------------------------------------------------------------
# 2. Primas por zona (texto) -> tabla consolidada
# ----------------------------------------------------------------------------------------------
# Primas porcentuales leídas del articulado (ver upc_valores_por_articulo.csv para la comprobación):
PRIMA_TEXTO = {
    ("C", "dispersion"): {y: 0.10 for y in range(2013, 2027)},
    ("C", "ciudades"): {**{2013: 0.0985}, **{y: 0.0986 for y in range(2014, 2027)}},
    ("C", "san_andres"): {y: 0.379 for y in range(2015, 2027)},
    ("S", "dispersion"): {y: 0.1147 for y in range(2013, 2027)},
    ("S", "ciudades"): {y: 0.15 for y in range(2013, 2027)},
    ("S", "san_andres"): {y: 0.379 for y in range(2015, 2019)},   # desde 2019 es un valor fijo (equiparación)
    ("S", "guainia"): {y: 0.1781 for y in range(2023, 2027)},
}


# Valores fijados que no salen de una tabla etaria legible y se leyeron en el texto OCR (línea citada)
VALORES_LEIDOS = [
    (2018, "S", "piloto_igualacion_prima_pura", "ciudades_piloto", 864568.80, "Artículo 19 (texto OCR, línea 577-581)"),
    (2018, "S", "indigena_epsi", "resto_pais", 754308.00, "Artículo 15 (texto OCR, línea 423-426: incremento del 4,81 %)"),
    (2021, "S", "general", "san_andres", 1266494.40, "Artículo 14 (texto OCR, línea 540-544)"),
    (2021, "S", "indigena_epsi", "resto_pais", 914464.80, "Artículo 15 (texto OCR, línea 580-583: incremento del 4,81 %)"),
]


def primas(art):
    filas = []
    for y in range(2013, 2027):
        for reg in "CS":
            b = BASE[(y, reg)]
            filas.append(dict(vigencia=y, regimen=reg, variante="general", zona="resto_pais", prima=0.0,
                              upc_anual=b, metodo="valor base del artículo 1 / 10-12", resolucion=RES[y]))
            for (r, z), d in PRIMA_TEXTO.items():
                if r != reg or y not in d:
                    continue
                a = art[(art.vigencia == y) & (art.regimen == reg) & (art.variante == "general") & (art.zona == z)]
                upc = round(b * (1 + d[y]), 2)
                if len(a):
                    ok = abs(a.razon_vs_base.iloc[0] - (1 + d[y])) < 0.0006
                    metodo = "prima del texto; confirmada con la tabla etaria del " + a.articulo.iloc[0] if ok else \
                        f"prima del texto ({d[y]:.2%}) NO coincide con la tabla etaria (razón {a.razon_vs_base.iloc[0]})"
                else:
                    metodo = "prima del texto x UPC base (tabla etaria no legible en la extracción)"
                filas.append(dict(vigencia=y, regimen=reg, variante="general", zona=z, prima=d[y], upc_anual=upc,
                                  metodo=metodo, resolucion=RES[y]))
    # zonas con valor fijo o variantes (indígena, piloto, inclusiones 2022, San Andrés RS desde 2019)
    extra = art[~((art.variante == "general") & art.zona.isin(["resto_pais", "dispersion", "ciudades"])) & (art.zona != "otro")]
    for r in extra.itertuples():
        if r.variante == "general" and (r.regimen, r.zona) in PRIMA_TEXTO and r.vigencia in PRIMA_TEXTO[(r.regimen, r.zona)]:
            continue
        filas.append(dict(vigencia=r.vigencia, regimen=r.regimen, variante=r.variante, zona=r.zona,
                          prima=round(r.razon_vs_base - 1, 4), upc_anual=r.upc_anual_implicita,
                          metodo="valor fijado en el " + r.articulo + " (derivado de su tabla etaria)", resolucion=RES[r.vigencia]))
    for y, reg, var, z, v, a in VALORES_LEIDOS:
        filas.append(dict(vigencia=y, regimen=reg, variante=var, zona=z, prima=round(v / BASE[(y, reg)] - 1, 4),
                          upc_anual=v, metodo="valor fijado en el " + a, resolucion=RES[y]))
    df = pd.DataFrame(filas).drop_duplicates(["vigencia", "regimen", "variante", "zona"]).reset_index(drop=True)
    # UPC indígena por zona cuando la tabla no fue legible: base indígena x (1 + prima de la zona del RS)
    ind = df[(df.variante == "indigena_epsi") & (df.zona == "resto_pais")]
    for r in ind.itertuples():
        for z, p in (("dispersion", 0.1147), ("ciudades", 0.15)):
            if not ((df.vigencia == r.vigencia) & (df.variante == "indigena_epsi") & (df.zona == z)).any():
                df = pd.concat([df, pd.DataFrame([dict(vigencia=r.vigencia, regimen="S", variante="indigena_epsi", zona=z,
                                       prima=round((1 + r.prima) * (1 + p) - 1, 4), upc_anual=round(r.upc_anual * (1 + p), 2),
                                       metodo=f"calculado: UPC indígena x (1 + {p:.2%}) según el artículo de la zona para EPSI", resolucion=RES[r.vigencia])])], ignore_index=True)
    return df.sort_values(["vigencia", "regimen", "variante", "zona"])


# ----------------------------------------------------------------------------------------------
# 3. Municipios por zona
# ----------------------------------------------------------------------------------------------
geo = pd.read_csv(GEO, dtype=str)
geo = geo[~geo.municipio.str.contains("SIN IDENTIFICAR|INPEC|NO DEFINIDO", na=False)]
NOM = {c: norm(re.sub(r"^\d{5}\s*-\s*", "", m)) for c, m in zip(geo.cod_municipio, geo.municipio)}
DEP = {c: norm(d) for c, d in zip(geo.cod_municipio, geo.departamento)}
POR_DP = {}
for c, n in NOM.items():
    POR_DP.setdefault(c[:2], []).append((n, c))
DEPTOS = {"05": "ANTIOQUIA", "08": "ATLANTICO", "11": "BOGOTA", "13": "BOLIVAR", "15": "BOYACA", "17": "CALDAS",
          "18": "CAQUETA", "19": "CAUCA", "20": "CESAR", "23": "CORDOBA", "25": "CUNDINAMARCA", "27": "CHOCO",
          "41": "HUILA", "44": "GUAJIRA", "47": "MAGDALENA", "50": "META", "52": "NARINO", "54": "NORTE DE SANTANDER",
          "63": "QUINDIO", "66": "RISARALDA", "68": "SANTANDER", "70": "SUCRE", "73": "TOLIMA", "76": "VALLE",
          "81": "ARAUCA", "85": "CASANARE", "86": "PUTUMAYO", "88": "SAN ANDRES", "91": "AMAZONAS", "94": "GUAINIA",
          "95": "GUAVIARE", "97": "VAUPES", "99": "VICHADA"}
DP_RX = sorted(DEPTOS.items(), key=lambda kv: -len(kv[1]))


def sim(a, b):
    return difflib.SequenceMatcher(None, a, b).ratio()


def por_nombre(linea):
    t = norm(linea)
    t = re.sub(r"\bVALLE DEL CAUCA\b", "VALLE", t)
    t = re.sub(r"\bNORTE (DE )?SANTANDER\b", "NORTE DE SANTANDER", t)
    t = re.sub(r"\bLA GUAJIRA\b", "GUAJIRA", t)
    t = re.sub(r"\bSANTIAGO DE CALI\b", "CALI", t)
    for dp, dn in DP_RX:
        k = t.find(dn)
        if k < 0:
            continue
        resto = re.sub(r"\b\d+\b", " ", (t[k + len(dn):] or t[:k])).strip()
        if not resto:
            return None
        best, sc = None, 0
        for n, c in POR_DP.get(dp, []):
            for cand in {resto, " ".join(resto.split()[:len(n.split())])}:
                r = sim(cand, n)
                if r > sc:
                    best, sc = c, r
        return best if sc >= 0.80 else None
    return None


def anexos_texto(y):
    """Anexos de dispersión (y ciudades en 2026) de las resoluciones con texto legible."""
    t = open(sorted(glob.glob(str(TXT / f"upc_vigencia-{y}_*[0-9].txt")))[0], encoding="utf-8", errors="ignore").read()
    L = t.splitlines()
    heads = [i for i, l in enumerate(L) if re.search(r"^\s*ANEXO\b", l.strip(), re.I)]
    filas = []
    if not any("DISPERSI" in norm(" ".join(L[i:i + 6])) for i in heads):
        i0 = next((i for i, l in enumerate(L) if re.match(r"^\s*1\s+\d{5}\s", l)), None)
        if i0 is not None:
            heads, L = [0], ["ANEXO dispersion"] + L[i0:]
    for k, i in enumerate(heads):
        j = heads[k + 1] if k + 1 < len(heads) else len(L)
        cab = norm(" ".join(L[i:i + 6]))
        if "DISPERSI" in cab:
            zona, reg = "dispersion", ("C" if "CONTRIBUTIVO" in cab else "S" if "SUBSIDIADO" in cab else "CS")
        elif "CIUDAD" in cab:
            zona, reg = "ciudades", "CS"
        else:
            continue
        for l in L[i:j]:
            cods = [c.translate(str.maketrans("OoIl", "0011")) for c in re.findall(r"(?<![\d.,$])([0-9OoIl]{5})(?![\d.,])", l)]
            cods = [c for c in cods if c[:2] in DEPTOS]
            cn = por_nombre(l)
            if not cods and not cn:
                continue
            c = cods[0] if cods else None
            if c in NOM and cn and cn != c and (c[:2] == cn[:2] and NOM[cn] in NOM[c]
                                                or max(sim(NOM[c], " ".join(norm(l).split()[-k2:])) for k2 in range(1, 6)) >= 0.75):
                cn = c
            if c in NOM and (cn is None or cn == c):
                filas.append((y, zona, reg, c, "código y nombre del anexo" if cn == c else "código del anexo"))
            elif cn:
                filas.append((y, zona, reg, cn, f"nombre del anexo (código impreso {c} corregido)" if c else "nombre del anexo"))
    return filas


def anexos_ocr(y, ref_prev, ref_next, total_esperado, vistos):
    """Años escaneados: códigos leídos por OCR de la columna Código (archivo en data/reference)."""
    ref = ref_prev | ref_next
    filas, seq, rows = [], [], [l.split() for l in open(OCR / f"{y}.txt") if l.strip()]
    for pg, n, c in rows:
        seq.append(c if c in ref else None)
    leidos = []
    for k, (pg, n, c) in enumerate(rows):
        if c in ref:
            leidos.append((c, "código leído por OCR"))
            continue
        cand = [r for r in ref if sum(a != b for a, b in zip(r, c)) == 1]
        if len(cand) > 1:
            prev = next((seq[i] for i in range(k - 1, -1, -1) if seq[i]), "00000")
            nxt = next((seq[i] for i in range(k + 1, len(seq)) if seq[i]), "99999")
            cand = [r for r in cand if prev < r < nxt]
        if len(cand) == 1:
            leidos.append((cand[0], f"código leído por OCR ({c}) corregido por un dígito"))
        elif c in NOM:
            leidos.append((c, "código leído por OCR (no figura en vigencias vecinas)"))
    got = {}
    for c, m in leidos:
        got.setdefault(c, m)
    faltan = (ref_prev & ref_next) - set(got)
    consistente = len(got) + len(faltan) == total_esperado and not (set(got) - ref)
    for c, m in got.items():
        filas.append((y, "dispersion", "CS", c, m))
    for c in sorted(faltan):
        if c in vistos:
            filas.append((y, "dispersion", "CS", c, "fila no legible por OCR; verificada visualmente en la imagen"))
        elif consistente:
            filas.append((y, "dispersion", "CS", c, f"fila no legible por OCR; inferida (anexo de {total_esperado} filas, "
                                                    "todas las demás coinciden con las vigencias anterior y siguiente)"))
    return filas


CIU = {"ARMENIA": "63001", "BARRANCABERMEJA": "68081", "BARRANQUILLA": "08001", "BELLO": "05088", "BOGOTA": "11001",
       "BUCARAMANGA": "68001", "BUENAVENTURA": "76109", "BUGA": "76111", "CALI": "76001", "CARTAGENA": "13001",
       "CARTAGO": "76147", "CUCUTA": "54001", "DOSQUEBRADAS": "66170", "FLORIDABLANCA": "68276", "IBAGUE": "73001",
       "ITAGUI": "05360", "MANIZALES": "17001", "MEDELLIN": "05001", "MONTERIA": "23001", "NEIVA": "41001",
       "PALMIRA": "76520", "PASTO": "52001", "PEREIRA": "66001", "POPAYAN": "19001", "PROVIDENCIA": "88564",
       "RIOHACHA": "44001", "SAN ANDRES": "88001", "SANTA MARTA": "47001", "SINCELEJO": "70001", "SOACHA": "25754",
       "SOLEDAD": "08758", "TULUA": "76834", "VALLEDUPAR": "20001", "VILLAVICENCIO": "50001"}


def ciudades_texto(y):
    """Listas de ciudades escritas en el articulado (2013-2025). Devuelve {régimen: set(códigos)}."""
    t = textos(y)[0]
    t = re.sub(r"RESOLUCI[ÓO]N N[ÚU]MER.{0,300}?(disposiciones|dictan otras)[\"”]?", " ", t)
    arts = [m.start() for m in RX_ART.finditer(t)]
    out = {}
    for m in re.finditer(r"(\d{1,2}(?:[.,]\d{1,2})?) ?% (?:(?:en|a) las ciudades (?:de )?|a ?la Unidad de Pago.{0,260}? a las (?:de )?ciudades (?:de )?)", t):
        if "Mantener" in t[max(0, m.start() - 300):m.start()]:
            continue
        a0 = max([a for a in arts if a < m.start()] or [0])
        clausula = t[a0:m.start()]
        if re.search(r"EPSI|EPS ?I ?03|ind[íi]gena|Sobre el valor fijado|Al valor fijado", clausula, re.I):
            continue                      # listas repetidas para EPS indígenas
        reg = "S" if m.group(1) == "15" else "C"
        fin = re.search(r"dando como|lo que corresponde|, respectivamente|Par[áa]grafo|ART[ÍI]CULO|Art[íi]culo", t[m.end():])
        n = norm(t[m.end(): m.end() + (fin.start() if fin else 900)])
        cods = {c for k, c in CIU.items() if re.search(r"\b" + k + r"\b", n)}
        for tok in set(n.split()):
            for k, c in CIU.items():
                if " " not in k and len(tok) >= 4 and sim(tok, k) >= 0.8:
                    cods.add(c)
        if re.search(r"\bRAGU\b", n):
            cods.add("05360")             # 2023: OCR de "Itagüí"
        out.setdefault(reg, cods)
    return out


def municipios():
    filas = []
    for y in list(range(2016, 2018)) + list(range(2019, 2021)) + list(range(2022, 2027)):
        filas += anexos_texto(y)
    df = pd.DataFrame(filas, columns=["vigencia", "zona", "regimen_anexo", "cod_municipio", "verificacion"])
    df = df.drop_duplicates(["vigencia", "zona", "regimen_anexo", "cod_municipio"])
    L = lambda y: set(df[(df.vigencia == y) & (df.zona == "dispersion")].cod_municipio)
    # filas revisadas a ojo sobre la imagen del anexo (ver docs/upc_zonas.md)
    visto = {2014: {"70110", "70400", "70678", "70702", "70713", "70717", "70771", "70820", "73873"},
             2018: {"70742", "94886", "97777"},
             2021: {"52385", "52473", "54800", "85325", "85410", "97511", "97777"}}
    ocr = []
    ocr += anexos_ocr(2018, L(2017), L(2019), 363, visto[2018])
    ocr += anexos_ocr(2021, L(2020), L(2022), 363, visto[2021])
    ocr += anexos_ocr(2015, L(2016), L(2016), 363, set())
    ocr += anexos_ocr(2014, L(2016), L(2016), 363, visto[2014])
    df = pd.concat([df, pd.DataFrame(ocr, columns=df.columns)])
    # 2014: el OCR leyó 13873 (Villanueva, Bolívar) donde la imagen dice 73873 (Villarrica, Tolima)
    df = df[~((df.vigencia == 2014) & (df.cod_municipio == "13873"))]
    extra = [[2022, "dispersion", "CS", "95200",
              "código ilegible en el PDF ('ozuu'); la fila 353 dice 'Miraflores' entre los municipios de Guaviare"]]
    # 2013: regla por departamentos
    deps13 = {"91", "81", "85", "18", "27", "44", "94", "95", "50", "86", "70", "97", "99"}
    uraba = {"05045", "05051", "05147", "05172", "05475", "05480", "05490", "05659", "05665", "05837", "05873"}
    for c in NOM:
        if c[:2] in deps13 or c in uraba:
            if c in ("81001", "18001", "85001"):
                continue
            v = ("departamento listado en el art. 2 / 11" if c[:2] in deps13 else
                 "región de Urabá (la resolución no la delimita; se usan los 11 municipios de la subregión Urabá antioqueño)")
            if c[:2] in ("81", "18", "85"):
                v += "; la excepción de Arauca, Florencia y Yopal incluye 'sus áreas de influencia', no delimitadas"
            extra.append([2013, "dispersion", "CS", c, v])
    # ciudades
    for y in range(2013, 2026):
        for reg, cods in ciudades_texto(y).items():
            for c in sorted(cods):
                extra.append([y, "ciudades", reg, c, "ciudad nombrada en el artículo de la prima para ciudades"])
    # piloto de igualación de prima pura del RS (2016-2018): Bogotá, Medellín, Cali y Barranquilla
    for y in (2016, 2017, 2018):
        for c in ("11001", "05001", "76001", "08001"):
            extra.append([y, "ciudades_piloto", "S", c, "prueba piloto de igualación de prima pura (art. 18-19)"])
    # San Andrés y Guainía
    for y in range(2015, 2027):
        for c in ("88001", "88564"):
            extra.append([y, "san_andres", "CS", c, "departamento Archipiélago (art. 4 / 14)"])
    for y in range(2023, 2027):
        for c in [c for c in NOM if c[:2] == "94"]:
            extra.append([y, "guainia", "S", c, "departamento de Guainía (UPC-S con prima de 17,81 %)"])
    df = pd.concat([df, pd.DataFrame(extra, columns=df.columns)], ignore_index=True)
    # expandir 'CS' a cada régimen
    out = []
    for r in df.itertuples():
        for reg in ("C", "S") if r.regimen_anexo == "CS" else (r.regimen_anexo,):
            out.append((int(r.vigencia), reg, r.zona, r.cod_municipio, r.verificacion))
    m = pd.DataFrame(out, columns=["vigencia", "regimen", "zona", "cod_municipio", "verificacion"])
    m = m.drop_duplicates(["vigencia", "regimen", "zona", "cod_municipio"])
    # Precedencia cuando un municipio aparece en dos listas: San Andrés > Guainía > ciudades piloto > ciudades > dispersión
    orden = {"san_andres": 0, "guainia": 1, "ciudades_piloto": 2, "ciudades": 3, "dispersion": 4}
    m["_o"] = m.zona.map(orden)
    dup = m.groupby(["vigencia", "regimen", "cod_municipio"]).zona.transform("nunique") > 1
    m.loc[dup, "verificacion"] += "; figura en más de una lista de la resolución (se asigna la de mayor precedencia)"
    m = m.sort_values("_o").drop_duplicates(["vigencia", "regimen", "cod_municipio"]).drop(columns="_o")
    m["departamento"] = m.cod_municipio.map(DEP)
    m["municipio"] = m.cod_municipio.map(NOM)
    m["resolucion"] = m.vigencia.map(RES)
    return m.sort_values(["vigencia", "regimen", "zona", "cod_municipio"])


def prima_etaria():
    """Cada código EPS del artículo de 'concentración de riesgo etario' recibe el primer porcentaje que le sigue."""
    filas = []
    for y in range(2013, 2027):
        t = textos(y)[0]
        for m in re.finditer(r"concentraci[óo]n de riesgo eta\w*", t):
            seg = t[m.end(): m.end() + 3000]
            fin = RX_ART.search(seg)
            seg = seg[: fin.start()] if fin else seg
            seg = re.sub(r"(?<!EPS037 )(?<!EPS 037 )\bNUEVA EPS\b", "EPS037", seg, flags=re.I)
            toks = [(x.start(), "eps", re.sub(r"\s", "", x.group(1))) for x in re.finditer(r"EPS ?(0\d\d)", seg)]
            toks += [(x.start(), "pct", x.group(1)) for x in re.finditer(r"(\d{1,2}(?:[.,]\d+)?) ?%", seg)]
            pend = []
            for _, k, v in sorted(toks):
                if k == "eps":
                    pend.append(v)
                elif pend:
                    p = float(v.replace(",", ".")) / 100
                    if p <= 0.10:
                        filas += [dict(vigencia=y, regimen="C", eps="EPS" + e, prima=p, resolucion=RES[y],
                                       fundamento="ponderador de concentración de riesgo etario (Acuerdo 026 de 2011 de la CRES)")
                                  for e in pend]
                    pend = []
    return pd.DataFrame(filas).drop_duplicates(["vigencia", "eps"])


if __name__ == "__main__":
    art = valores_por_articulo()
    art.to_csv(OUT / "upc_valores_por_articulo.csv", index=False, encoding="utf-8")
    pz = primas(art)
    pz.to_csv(OUT / "upc_primas_zona.csv", index=False, encoding="utf-8")
    mz = municipios()
    mz.to_csv(OUT / "upc_municipio_zona.csv", index=False, encoding="utf-8")
    pe = prima_etaria()
    pe.to_csv(OUT / "upc_prima_etaria_eps.csv", index=False, encoding="utf-8")
    print(art.groupby(["vigencia", "regimen"]).size().unstack().to_string())
    print(pz[pz.variante == "general"].pivot_table(index="vigencia", columns=["regimen", "zona"], values="prima").round(4).to_string())
    print(mz.groupby(["vigencia", "regimen", "zona"]).size().unstack(fill_value=0).to_string())
    print(pe.to_string())
