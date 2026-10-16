"""
Descarga (o actualiza) las fuentes crudas del repositorio desde los portales oficiales.
Pensado para correr cada mes desde el computador del mantenedor.

  python scripts/00_descargar_fuentes.py minsalud      # ZIP mensuales de Cifras de afiliación
  python scripts/00_descargar_fuentes.py adres         # foto vigente BDUA (datos.gov.co), agregada
  python scripts/00_descargar_fuentes.py sispro        # serie mensual del cubo BDUA (Power BI público)
  python scripts/00_descargar_fuentes.py upc           # resoluciones de UPC listadas en docs/fuentes.json
  python scripts/00_descargar_fuentes.py todo

Requiere: pip install requests pandas

Notas
- MinSalud y SISPRO pueden bloquear peticiones automatizadas; si una descarga falla, baje el
  archivo con el navegador y guárdelo en la carpeta indicada con el mismo nombre.
- El tablero de SISPRO es un informe "publicar en la web" de Power BI. Este script hace las
  mismas consultas que el visor hace al abrir el tablero (endpoint público querydata).
  Si MinSalud cambia el informe, actualice RESOURCE_KEY y los nombres de tabla/columna.
"""
from pathlib import Path
import datetime as dt
import gzip
import io
import json
import re
import sys

import requests

RAIZ = Path(__file__).resolve().parents[1]
RAW = RAIZ / "data" / "raw"
UA = {"User-Agent": "Mozilla/5.0 (repositorio afiliacion-salud-colombia; uso académico)"}
MESES = {"enero": 1, "ene": 1, "febrero": 2, "feb": 2, "marzo": 3, "mar": 3, "abril": 4, "abr": 4,
         "mayo": 5, "may": 5, "junio": 6, "jun": 6, "julio": 7, "jul": 7, "agosto": 8, "ago": 8,
         "septiembre": 9, "sep": 9, "sept": 9, "octubre": 10, "oct": 10, "noviembre": 11, "nov": 11,
         "diciembre": 12, "dic": 12}


# ----------------------------------------------------------------------------- MinSalud
def minsalud():
    pagina = "https://minsalud.gov.co/Proteccion-Social/Paginas/cifras-aseguramiento-salud.aspx"
    html = requests.get(pagina, headers=UA, timeout=60).text
    destino = RAW / "minsalud_cifras_afiliacion"
    destino.mkdir(parents=True, exist_ok=True)
    for url in sorted(set(re.findall(r'href="([^"]+\.zip)"', html))):
        url = requests.compat.urljoin(pagina, url)
        nombre = url.rsplit("/", 1)[-1].lower()
        mes = next((v for k, v in sorted(MESES.items(), key=lambda kv: -len(kv[0])) if k in nombre), None)
        anio = re.search(r"(20\d{2})", nombre)
        if not (mes and anio):
            print("  ? no se reconoce el mes en", nombre)
            continue
        f = destino / f"cifras-afiliacion-salud-{anio.group(1)}-{mes:02d}.zip"
        if f.exists():
            continue
        print("  descargando", url)
        f.write_bytes(requests.get(url, headers=UA, timeout=300).content)


# ----------------------------------------------------------------------------- ADRES
ADRES = {"contributivo": "tq4m-hmg2", "subsidiado": "d7a5-cnra"}
CAMPOS = ("dpr_nombre,mnc_nombre,ent_id,ent_nombre,tps_rgm_nombre,tps_est_afl_nombre,"
          "tps_gnr_nombre,tps_grp_etr_id,zns_nombre")


def adres():
    meta = requests.get("https://www.datos.gov.co/api/views/d7a5-cnra.json", timeout=60).json()
    actualizado = dt.datetime.utcfromtimestamp(meta["rowsUpdatedAt"])
    # El corte de la BDUA es el mes anterior a la publicación
    corte = (actualizado.replace(day=1) - dt.timedelta(days=1)).strftime("%Y-%m")
    destino = RAW / "adres_datos_abiertos" / f"corte-{corte}"
    destino.mkdir(parents=True, exist_ok=True)
    for reg, ident in ADRES.items():
        f = destino / f"bdua_{reg}_agregado.csv.gz"
        if f.exists():
            continue
        url = (f"https://www.datos.gov.co/resource/{ident}.csv?$select={CAMPOS},"
               f"sum(cantidad::number) as afiliados&$group={CAMPOS}&$order={CAMPOS}&$limit=5000000")
        print("  descargando", reg, "corte", corte)
        f.write_bytes(gzip.compress(requests.get(url, timeout=900).content))
    (destino / "metadatos.json").write_text(json.dumps(
        {"fecha_publicacion_adres": actualizado.isoformat(), "consulta_soql": CAMPOS,
         "conjuntos": ADRES}, ensure_ascii=False, indent=1), encoding="utf-8")


# ----------------------------------------------------------------------------- SISPRO
RESOURCE_KEY = "fcd78c4a-6976-4ef2-9a76-729fd6bf41cb"
CLUSTER = "https://wabi-paas-1-scus-api.analysis.windows.net/public/reports/"
TABLA = "CU_BDUA (2)"


def _pbi_post(cuerpo):
    h = {"X-PowerBI-ResourceKey": RESOURCE_KEY, "Content-Type": "application/json;charset=UTF-8"}
    r = requests.post(CLUSTER + "querydata?synchronous=true", headers=h, json=cuerpo, timeout=120)
    r.raise_for_status()
    return r.json()


def _pbi_consulta(modelo, columnas, agregada, filtro_mes=None, n=60000):
    col = lambda p: {"Column": {"Expression": {"SourceRef": {"Source": "c"}}, "Property": p}}
    sel = [dict(col(p), Name=f"s{i}") for i, p in enumerate(columnas)]
    sel.append({"Aggregation": {"Expression": col(agregada), "Function": 0}, "Name": "a"})
    where = []
    if filtro_mes:
        where = [{"Condition": {"In": {"Expressions": [col("Fecha Corte.Mesanno")],
                                       "Values": [[{"Literal": {"Value": f"'{filtro_mes}'"}}]]}}}]
    q = {"Version": 2, "From": [{"Name": "c", "Entity": TABLA, "Type": 0}], "Select": sel, "Where": where}
    cuerpo = {"version": "1.0.0", "queries": [{"Query": {"Commands": [{"SemanticQueryDataShapeCommand": {
        "Query": q, "Binding": {"Primary": {"Groupings": [{"Projections": list(range(len(sel)))}]},
                                "DataReduction": {"DataVolume": 4, "Primary": {"Window": {"Count": n}}},
                                "Version": 1}}}]},
        "QueryId": "", "ApplicationContext": {"DatasetId": modelo["dbName"], "Sources": [{"ReportId": "x"}]}}],
        "cancelQueries": [], "modelId": modelo["id"]}
    return _decodificar(_pbi_post(cuerpo))


def _decodificar(r):
    """Descomprime el formato DSR de Power BI (bits R = repite valor anterior, Ø = nulo)."""
    ds = r["results"][0]["result"]["data"]["dsr"]["DS"][0]
    dic = ds.get("ValueDicts", {})
    filas, esquema, prev = [], None, []
    for fila in ds["PH"][0]["DM0"]:
        esquema = fila.get("S", esquema)
        rep, nul, c, k, out = fila.get("R", 0), fila.get("Ø", 0), fila.get("C", []), 0, []
        for i, s in enumerate(esquema):
            if rep & (1 << i):
                out.append(prev[i]); continue
            if nul & (1 << i):
                out.append(None); continue
            v = c[k]; k += 1
            if "DN" in s and isinstance(v, int):
                v = dic[s["DN"]][v]
            out.append(v)
        prev = out
        filas.append(out)
    if not ds.get("IC", True):
        raise RuntimeError("Respuesta incompleta de Power BI: reduzca el tamaño de la consulta")
    return filas


def sispro():
    h = {"X-PowerBI-ResourceKey": RESOURCE_KEY}
    me = requests.get(CLUSTER + RESOURCE_KEY + "/modelsAndExploration?preferReadOnlySession=true",
                      headers=h, timeout=60).json()
    modelo = me["models"][0]
    meses = [f[0] for f in _pbi_consulta(modelo, ["Fecha Corte.Mesanno"], "Total", n=1000)]
    destino = RAW / "sispro_cubo_bdua"
    destino.mkdir(parents=True, exist_ok=True)
    lineas = ["periodo,cod_municipio,regimen,estado_afiliacion,afiliados"]
    for m in meses:
        filas = _pbi_consulta(modelo, ["Geografia.Codigo de Municipio", "Regimen.Tipo Regimen",
                                       "Estado Afiliacion.Estado"], "Total", filtro_mes=m)
        lineas += [f'{m},{a},{b},"{c}",{d}' for a, b, c, d in filas]
        print("  ", m, len(filas))
    with gzip.open(destino / "municipio_regimen_estado_mensual.csv.gz", "wt", encoding="utf-8") as fh:
        fh.write("\n".join(lineas))
    geo = _pbi_consulta(modelo, ["Geografia.Codigo de Municipio", "Geografia.Departamento",
                                 "Geografia.Municipio", "Geografia.Categorias Ruralidad",
                                 "Geografia.Areas de Gestión"], "Total", n=5000)
    with open(destino / "geografia.csv", "w", encoding="utf-8") as fh:
        fh.write("cod_municipio,departamento,municipio,categoria_ruralidad,area_gestion\n")
        for g in geo:
            fh.write(",".join(f'"{x or ""}"' for x in g[:5]) + "\n")


# ----------------------------------------------------------------------------- UPC
def upc():
    fuentes = json.loads((RAIZ / "docs" / "fuentes.json").read_text(encoding="utf-8"))
    for n in fuentes["normas"]:
        f = RAIZ / n["archivo_local"]
        if f.exists():
            continue
        f.parent.mkdir(parents=True, exist_ok=True)
        print("  descargando", n["url"])
        f.write_bytes(requests.get(n["url"], headers=UA, timeout=120).content)


if __name__ == "__main__":
    que = sys.argv[1] if len(sys.argv) > 1 else "todo"
    for nombre, fn in [("minsalud", minsalud), ("adres", adres), ("sispro", sispro), ("upc", upc)]:
        if que in (nombre, "todo"):
            print(f"== {nombre}")
            fn()
