"""Funciones compartidas: normalización de nombres y cruce con códigos DANE (DIVIPOLA)."""
from pathlib import Path
import re
import unicodedata
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
GEO = RAIZ / "data" / "raw" / "sispro_cubo_bdua" / "geografia.csv"


def norm(s) -> str:
    s = str(s).replace("¥", "N")
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().upper()
    s = re.sub(r"^\d{5}\s*-\s*", "", s)
    s = re.sub(r"\(?\bCD\b\.?\)?", " ", s)          # "(CD.)" = corregimiento departamental
    s = re.sub(r"[^A-Z0-9() ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def variantes(nombre: str) -> set:
    """'ALTO BAUDO (PIE DE PATO)' -> {'ALTO BAUDO PIE DE PATO', 'ALTO BAUDO', 'PIE DE PATO'}"""
    n = norm(nombre)
    sin = re.sub(r"\(.*?\)", " ", n)
    dentro = " ".join(re.findall(r"\((.*?)\)", n))
    out = {re.sub(r"[()]", " ", n), sin, dentro}
    return {re.sub(r"\s+", " ", x).strip() for x in out if x.strip()}


# Nombres abreviados o antiguos usados en la BDUA -> nombre DIVIPOLA (normalizado)
ALIAS = {
    ("ANTIOQUIA", "ANTIOQUIA"): "SANTAFE DE ANTIOQUIA",
    ("ANTIOQUIA", "BOLIVAR"): "CIUDAD BOLIVAR",
    ("ANTIOQUIA", "CARMEN DE VIBORAL"): "EL CARMEN DE VIBORAL",
    ("ANTIOQUIA", "SANTUARIO"): "EL SANTUARIO",
    ("ATLANTICO", "POLO NUEVO"): "POLONUEVO",
    ("BOYACA", "PAZ DE RIO"): "PAZ DEL RIO",
    ("BOYACA", "TUTASA"): "TUTAZA",
    ("BOYACA", "VILLA DE LEYVA"): "VILLA DE LEIVA",
    ("CALDAS", "SAN JOSE DE CALDAS"): "SAN JOSE DE FRAGUA",   # 17665: así aparece en la geografía SISPRO
    ("CAQUETA", "SAN JOSE DE FRAGUA"): "SAN JOSE DEL FRAGUA",
    ("CAUCA", "LOPEZ DE MICAY"): "LOPEZ",
    ("CESAR", "CODAZZI"): "AGUSTIN CODAZZI",
    ("CESAR", "LA PAZ ROBLES"): "ROBLES",
    ("CHOCO", "CANTON DE SAN PABLO"): "EL CANTON DE SAN PABLO",
    ("CHOCO", "EL CARMEN"): "EL CARMEN DE ATRATO",
    ("CHOCO", "ITSMINA"): "ISTMINA",
    ("CUNDINAMARCA", "EL PENOL"): "EL PENON",
    ("CUNDINAMARCA", "S ANTONIO TEQUENDAMA"): "SAN ANTONIO DEL TEQUENDAMA",
    ("CUNDINAMARCA", "SAN JUAN DE RIO SECO"): "SAN JUAN DE RIOSECO",
    ("GUAINIA", "INIRIDA"): "PUERTO INIRIDA",
    ("GUAINIA", "MORICHAL NUEVO"): "MORICHAL",
    ("GUAINIA", "DPTO GUAINIA"): "GUAINIA TOTAL",
    ("VAUPES", "DPTO VAUPES"): "VAUPES TOTAL",
    ("VAUPES", "PAPUNAHUA"): "PAPUNAUA",
    ("AMAZONAS", "PTO SANTANDER"): "PUERTO SANTANDER",
    ("AMAZONAS", "MIRITINPARANA"): "MIRITI PARANA",
    ("MAGDALENA", "EL PIJINO DEL CARMEN"): "PIJINO DEL CARMEN",
    ("MAGDALENA", "SABANA DE SAN ANGEL"): "SABANAS DE SAN ANGEL",
    ("MAGDALENA", "SAN SEBASTIAN BUENAVIST"): "SAN SEBASTIAN DE BUENAVISTA",
    ("META", "SAN CARLOS GUAROA"): "SAN CARLOS DE GUAROA",
    ("META", "VISTA HERMOSA"): "VISTAHERMOSA",
    ("NARINO", "EL TABLON"): "EL TABLON DE GOMEZ",
    ("NARINO", "FRANCIS PIZARRO"): "FRANCISCO PIZARRO",
    ("NARINO", "LEYVA"): "LEIVA",
    ("RISARALDA", "DOS QUEBRADAS"): "DOSQUEBRADAS",
    ("SANTANDER", "EL CARMEN"): "EL CARMEN DE CHUCURI",
    ("TOLIMA", "GUAYABAL"): "ARMERO",
    ("TOLIMA", "VILLA HERMOSA"): "VILLAHERMOSA",
    ("VALLE", "SANTIAGO DE CALI"): "CALI",
}
ALIAS_DEPTO = {"VALLE DEL CAUCA": "VALLE", "GUAJIRA": "LA GUAJIRA", "NORTE SANTANDER": "NORTE DE SANTANDER",
               "BOGOTA": "BOGOTA D C", "BOGOTA D C ": "BOGOTA D C",
               "ARCHIPIELAGO DE SAN ANDRES PROVIDENCIA Y SANTA CATALINA": "SAN ANDRES"}


def cargar_cruce():
    geo = pd.read_csv(GEO, dtype=str)
    cruce = {}
    for d, m, c in zip(geo["departamento"], geo["municipio"], geo["cod_municipio"]):
        for v in variantes(m):
            cruce.setdefault((norm(d), v), c)
    return cruce


def codigo_dane(cruce, depto, mpio):
    d = norm(depto)
    d = ALIAS_DEPTO.get(d, d)
    m = re.sub(r"[()]", " ", norm(mpio))
    m = re.sub(r"\s+", " ", m).strip()
    m = ALIAS.get((d, m), m)
    for v in [m] + sorted(variantes(m)):
        if (d, v) in cruce:
            return cruce[(d, v)]
    return None
