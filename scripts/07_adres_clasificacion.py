"""
Agrupa la ejecución presupuestal de la ADRES en categorías comparables entre 2017 y hoy,
y deflacta con el IPC del DANE.

Criterio: se clasifican solo las HOJAS del árbol de rubros de cada mes (el rubro más
desagregado), según el nombre del concepto, porque los códigos cambiaron en 2020 (paso al
Catálogo de Clasificación Presupuestal, CCP) y también cambian algunos nombres. Cada regla
lleva su justificación en data/reference/adres_clasificacion_rubros.csv. Lo que no cae en
ninguna regla queda como "otros" con el nombre original, para revisarlo, no se esconde.

Entradas:
  data/processed/adres_ejecucion_rubros_mensual.csv
  data/raw/dane/anex-IPC-Indices-sep2026.xlsx
Salidas:
  data/processed/adres_ejecucion_categorias_mensual.csv  (periodo, tipo, medida, categoria,
        subcategoria, situacion_fondos, valor_mes_corriente, valor_mes_constante, ...)
  data/processed/ipc_dane_mensual.csv
  data/processed/adres_hojas_no_clasificadas.csv  (control de calidad)
"""
from pathlib import Path
import re
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
PROC = RAIZ / "data" / "processed"
BASE_IPC = "2026-09"

# (tipo, categoría, subcategoría, patrón regex sobre el concepto en mayúsculas). Orden = prioridad.
REGLAS = [
    # ---------------- GASTOS ----------------
    ("gasto", "Saneamiento de deudas (Ley 1955/2019 y Ley 2294/2023)", "Financiación de obligaciones art. 245 Ley 1955", r"ART\.? ?245|FINANCIACI[ÓO]N DE OBLIGACIONES"),
    ("gasto", "Saneamiento de deudas (Ley 1955/2019 y Ley 2294/2023)", "Glosa transversal / art. 237 Ley 1955", r"GLOSA TRANSVERSAL|ART\.? ?237|PUNTO FINAL|SANEAMIENTO"),
    ("gasto", "Saneamiento de deudas (Ley 1955/2019 y Ley 2294/2023)", "Pasivos art. 153 Ley 2294/2023", r"2294|ART\.? ?153"),
    ("gasto", "Saneamiento de deudas (Ley 1955/2019 y Ley 2294/2023)", "Deudas régimen subsidiado art. 275 Ley 1450/2011", r"ART[ÍI]CULO 275|ART\.? ?275"),
    ("gasto", "Operaciones financieras (compra de cartera, tasa compensada)", "Compra de cartera y fortalecimiento patrimonial", r"COMPRA DE CARTERA|TASA COMPENSADA|FORTALECIMIENTO PATRIMONIAL"),
    ("gasto", "No UPC: otros servicios no financiados", "Servicios no financiados con PM / compra centralizada", r"NO FINANCIAD|COMPRA CENTRALIZADA|SERVICIOS COMPLEMENTARIOS"),
    ("gasto", "No UPC: presupuestos máximos", "Ajuste/reajuste de vigencias anteriores - contributivo", r"AJUSTE.*PRESUPUESTOS? M[ÁA]XIMOS.*(CONTRIBUTIVO|R\.?C)"),
    ("gasto", "No UPC: presupuestos máximos", "Ajuste/reajuste de vigencias anteriores - subsidiado", r"AJUSTE.*PRESUPUESTOS? M[ÁA]XIMOS.*(SUBSIDIADO|R\.?S)"),
    ("gasto", "No UPC: presupuestos máximos", "Ajuste/reajuste de vigencias anteriores", r"AJUSTE.*PRESUPUESTOS? M[ÁA]XIMOS|REAJUSTE"),
    ("gasto", "No UPC: presupuestos máximos", "Contributivo", r"PRESUPUESTOS? M[ÁA]XIMOS?.*(CONTRIBUTIVO|R\.?C\b)"),
    ("gasto", "No UPC: presupuestos máximos", "Subsidiado", r"PRESUPUESTOS? M[ÁA]XIMOS?.*(SUBSIDIADO|R\.?S\b)"),
    ("gasto", "No UPC: presupuestos máximos", "Sin régimen identificado", r"PRESUPUESTOS? M[ÁA]XIMOS?"),
    ("gasto", "No UPC: recobros", "Recobros régimen subsidiado", r"RECOBRO.*SUBSIDIADO|NO PBS.*SUBSIDIADO|NO POS.*SUBSIDIADO"),
    ("gasto", "No UPC: recobros", "Recobros régimen contributivo", r"RECOBRO|REEMBOLSO|NO PBS|NO POS|TUTELA|CTC"),
    ("gasto", "UPC régimen contributivo", "Promoción y prevención (per cápita)", r"PROMOCI[ÓO]N Y PREVENCI[ÓO]N"),
    ("gasto", "UPC régimen contributivo", "UPC contributivo", r"UPC.*CONTRIBUTIVO|UNIDAD DE PAGO POR CAPITACI[ÓO]N.*CONTRIBUTIVO|COMPENSACI[ÓO]N"),
    ("gasto", "UPC régimen subsidiado", "UPC subsidiado", r"UPC.*(SUBSIDIADO|R\.?S\.?)|UNIDAD DE PAGO POR CAPITACI[ÓO]N.*SUBSIDIADO|LIQUIDACI[ÓO]N MENSUAL"),
    ("gasto", "Incapacidades y licencias", "Incapacidades", r"INCAPACIDAD"),
    ("gasto", "Incapacidades y licencias", "Licencias de maternidad y paternidad", r"LICENCIA"),
    ("gasto", "Incapacidades y licencias", "Prestaciones económicas regímenes especial y de excepción", r"PRESTACIONES ECON[ÓO]MICAS"),
    ("gasto", "Víctimas, tránsito y eventos catastróficos", "Accidentes de tránsito / SOAT", r"TR[ÁA]NSITO|SOAT"),
    ("gasto", "Víctimas, tránsito y eventos catastróficos", "Víctimas y eventos catastróficos", r"V[ÍI]CTIMA|CATASTR|TERRORIS|EMERGENCIAS Y DESASTRES|AUXILIO FUNERARIO|INDEMNIZACI"),
    ("gasto", "Emergencia COVID-19 (FOME y otros)", "COVID-19", r"COVID|FOME|CORONAVIRUS|PRUEBAS|CANASTA|EMERGENCIA SANITARIA|COMPENSACI[ÓO]N ECON[ÓO]MICA|AISLAMIENTO|TALENTO HUMANO|VACUN"),
    ("gasto", "Programas y transferencias del sector", "Residencias médicas", r"RESIDENCIAS M[ÉE]DICAS"),
    ("gasto", "Programas y transferencias del sector", "Supersalud (inspección, vigilancia y control)", r"SUPERINTENDENCIA|SUPERNITENDENCIA|SUPERSALUD|\bIVC\b|CONTRIBUCI[ÓO]N DE VIGILANCIA"),
    ("gasto", "Programas y transferencias del sector", "Funcionamiento de la ADRES", r"FUNCIONAMIENTO Y OPERACI[ÓO]N DE ADRES|GASTOS DE ADMINISTRACI[ÓO]N|OBJETO ADRES|0,5%"),
    ("gasto", "Programas y transferencias del sector", "Cajas de compensación / FOSFEC", r"FOSFEC|\bCCF\b"),
    ("gasto", "Programas y transferencias del sector", "Internos de medicina", r"INTERNOS DE MEDICINA"),
    ("gasto", "Programas y transferencias del sector", "Población migrante y zonas de frontera", r"MIGRANTE|FRONTERIZ|EXTRANJEROS"),
    ("gasto", "Programas y transferencias del sector", "Aportes patronales y ESE", r"APORTES PATRONALES|\bESE'?\u00b4?S?\b|FONSAET|HOSPITAL"),
    ("gasto", "Programas y transferencias del sector", "Programas MinSalud / destinación específica", r"PROGRAMA|MINISTERIO|MINSALUD|DESTINACI[ÓO]N|DEUDA RECONOCIDA|INFRAESTRUCTURA|SANEAMIENTO FISCAL|PREVENCI[ÓO]N|LABORATORIO|CAMPA[ÑN]A|SALUD P[ÚU]BLICA|VIOLENCIA"),
    ("gasto", "Devoluciones, rendimientos y otros pasivos", "Devoluciones y reprogramaciones", r"DEVOLUCI|REPROGRAMACI|REINTEGRO|PASIVO|SENTENCIA|CONCILIACI"),
    ("gasto", "Devoluciones, rendimientos y otros pasivos", "Rendimientos financieros reconocidos a EPS", r"RENDIMIENTO"),
    ("gasto", "Disponibilidad final", "Disponibilidad final", r"DISPONIBILIDAD FINAL"),
    # ---------------- INGRESOS ----------------
    ("ingreso", "Disponibilidad inicial", "Disponibilidad inicial", r"DISPONIBILIDAD INICIAL"),
    ("ingreso", "Cotizaciones régimen contributivo", "Cotizaciones adicionales", r"ADICIONAL(ES)? EN SALUD"),
    ("ingreso", "Cotizaciones régimen contributivo", "Cotizaciones", r"COTIZACI|R[ÉE]GIMEN CONTRIBUTIVO (CSF|SSF)"),
    ("ingreso", "Solidaridad de regímenes de excepción y especiales", "Solidaridad REX", r"EXCEPCI|\bREX\b|SOLIDARI"),
    ("ingreso", "Cajas de compensación familiar (art. 217 Ley 100)", "Aportes CCF", r"CAJAS? DE COMPENSACI|\bCCF\b"),
    ("ingreso", "Sistema General de Participaciones (SGP)", "SGP otros (FONSAET, aportes patronales, libre inversión)", r"SGP"),
    ("ingreso", "Sistema General de Participaciones (SGP)", "SGP régimen subsidiado", r"PARTICIPACIONES"),
    ("ingreso", "Presupuesto General de la Nación (PGN)", "Impuesto de renta con destinación a salud (CREE / Imporenta)", r"CREE|IMPORENTA|IMPUESTO SOBRE LA RENTA"),
    ("ingreso", "Operaciones financieras (compra de cartera, tasa compensada)", "Amortización compra de cartera", r"COMPRA DE CARTERA|TASA COMPENSADA"),
    ("ingreso", "Otros ingresos", "USPEC – población privada de la libertad", r"USPEC|PRIVADA DE LA LIBERTAD"),
    ("ingreso", "Otros ingresos", "Internos de medicina", r"INTERNOS DE MEDICINA"),
    ("ingreso", "Recursos de entidades territoriales", "Coljuegos", r"COLJUEGOS|JUEGOS DE SUERTE"),
    ("ingreso", "Recursos de entidades territoriales", "Fonpet", r"FONPET"),
    ("ingreso", "Recursos de entidades territoriales", "Departamentos, distritos y municipios", r"DEPARTAMENT|DISTRIT|MUNICIP|ENTIDADES TERRITORIALES|\bET\b|ESFUERZO PROPIO|RENTAS CEDIDAS|CERVEZA|LICORES|CIGARRILLO|TABACO"),
    ("ingreso", "Recursos de entidades territoriales", "Regalías", r"REGAL[ÍI]AS"),
    ("ingreso", "SOAT y FONSAT", "SOAT y FONSAT", r"SOAT|FONSAT"),
    ("ingreso", "Impuesto social a las armas y municiones", "Armas y municiones", r"MUNICIONES|ARMAS"),
    ("ingreso", "Presupuesto General de la Nación (PGN)", "Saneamiento de deudas", r"ART\.? ?2(37|45)|2294|ART\.? ?153|FINANCIACI[ÓO]N DE OBLIGACIONES|PASIVO"),
    ("ingreso", "Presupuesto General de la Nación (PGN)", "Emergencia COVID-19 (FOME)", r"FOME|COVID|EMERGENCIA"),
    ("ingreso", "Presupuesto General de la Nación (PGN)", "Aseguramiento en salud", r"APORTES? DE LA NACI[ÓO]N.*ASEGURAMIENTO|CIERRE|CR[ÉE]DITO|\bBID\b|\bBIRF\b"),
    ("ingreso", "Presupuesto General de la Nación (PGN)", "Otros aportes de la Nación", r"NACI[ÓO]N|RESIDENCIAS|PGN|PRESUPUESTO GENERAL"),
    ("ingreso", "Reintegros y recuperaciones", "Reintegros", r"REINTEGRO|RECUPERACI|VIGENCIAS ANTERIORES|DEVOLUCI|RESTITUCI|REPETICI"),
    ("ingreso", "Rendimientos financieros", "Rendimientos", r"RENDIMIENTO|INTERES"),
    ("ingreso", "Otros ingresos", "Excedentes y otros", r"EXCEDENTE|OTROS|MULTA|SANCI"),
]


# Justificación de cada categoría (se exporta a data/reference/adres_clasificacion_rubros.csv)
JUSTIFICACION = {
    "Saneamiento de deudas (Ley 1955/2019 y Ley 2294/2023)":
        "Pagos de cuentas de vigencias anteriores (servicios ya prestados), no gasto corriente del año. Se separan para no "
        "inflar el gasto no UPC del año en que se pagan. El art. 237 de la Ley 1955 de 2019 creó el mecanismo de saneamiento "
        "(auditoría de recobros) citado en la Resolución 94 de 2020; los demás rubros se identifican por el nombre que les da la ADRES.",
    "Operaciones financieras (compra de cartera, tasa compensada)":
        "Movimientos de liquidez hacia EPS/IPS que se recuperan; no son gasto en servicios de salud.",
    "No UPC: otros servicios no financiados":
        "Servicios y tecnologías no financiados con la UPC que la ADRES paga por fuera del techo de presupuestos máximos.",
    "No UPC: presupuestos máximos":
        "Ley 1955 de 2019, art. 240: desde 2020 los servicios no financiados con la UPC los gestionan las EPS con un techo "
        "anual (presupuesto máximo) que transfiere la ADRES, en ambos regímenes. Sustituye al recobro. Incluye ajustes y "
        "reajustes de techos de vigencias anteriores (ver autos 2881 de 2023 y 2049 de 2024 de la Corte Constitucional).",
    "No UPC: recobros":
        "Hasta 2019, la ADRES (antes Fosyga) pagaba por recobro los servicios no POS/no PBS del régimen contributivo. Los del "
        "subsidiado los pagaban los departamentos y no pasan por la ADRES; el art. 231 de la Ley 1955 de 2019 trasladó a la "
        "Nación ese pago desde el 1 de enero de 2020 (Resolución 94 de 2020). Por eso la serie no UPC de la ADRES antes de 2020 "
        "no incluye el subsidiado.",
    "UPC régimen contributivo":
        "Reconocimiento de la UPC del contributivo (proceso de compensación) y del per cápita de promoción y prevención. "
        "Hasta 2022 una parte se registraba sin situación de fondos (SSF): las cotizaciones que la EPS descontaba antes de girar.",
    "UPC régimen subsidiado":
        "Liquidación mensual de afiliados del subsidiado (LMA): UPC que la ADRES reconoce a las EPS del subsidiado. Incluye "
        "la parte financiada con SGP y esfuerzo propio territorial, que se registra sin situación de fondos.",
    "Incapacidades y licencias": "Prestaciones económicas del contributivo (no son servicios de salud).",
    "Víctimas, tránsito y eventos catastróficos": "Subcuenta ECAT del antiguo Fosyga: accidentes de tránsito, eventos catastróficos y terroristas.",
    "Emergencia COVID-19 (FOME y otros)": "Gastos temporales de la emergencia sanitaria 2020-2022.",
    "Programas y transferencias del sector": "Destinaciones específicas que la ADRES gira a otras entidades o programas.",
    "Devoluciones, rendimientos y otros pasivos": "Devoluciones de aportes, rendimientos y pasivos; no son gasto en salud del año.",
    "Disponibilidad final": "Saldo no ejecutado al cierre (se muestra aparte).",
}
GRUPO_EMPALME = {
    "No UPC: recobros": "No UPC (recobros hasta 2019 + presupuestos máximos desde 2020)",
    "No UPC: presupuestos máximos": "No UPC (recobros hasta 2019 + presupuestos máximos desde 2020)",
    "No UPC: otros servicios no financiados": "No UPC (recobros hasta 2019 + presupuestos máximos desde 2020)",
    "UPC régimen contributivo": "UPC", "UPC régimen subsidiado": "UPC",
}


def clasificar(tipo, concepto):
    c = re.sub(r"\s+", " ", str(concepto)).upper()
    for t, cat, sub, rx in REGLAS:
        if t == tipo and re.search(rx, c):
            return cat, sub
    return "Otros sin clasificar", str(concepto)


def situacion(concepto):
    c = str(concepto).upper()
    return "SSF" if re.search(r"\bSSF\b", c) else ("CSF" if re.search(r"\bCSF\b", c) else "")


def hojas(g):
    cods = set(g["codigo"])
    return g[[not any(o != c and o.startswith(c + "-") for o in cods) for c in g["codigo"]]]


def ipc():
    f = RAIZ / "data" / "raw" / "dane" / "anex-IPC-Indices-sep2026.xlsx"
    d = pd.read_excel(f, header=None)
    h = d.index[d.iloc[:, 0].astype(str).str.strip().eq("Mes")][0]
    anios = d.iloc[h, 1:].tolist()
    meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto",
             "Septiembre", "Octubre", "Noviembre", "Diciembre"]
    out = []
    for i, m in enumerate(meses, start=1):
        fila = d[d.iloc[:, 0].astype(str).str.strip().eq(m)].iloc[0, 1:].tolist()
        for a, v in zip(anios, fila):
            if pd.notna(a) and pd.notna(v):
                out.append((f"{int(a)}-{i:02d}", float(v)))
    s = pd.DataFrame(out, columns=["periodo", "ipc"]).sort_values("periodo")
    s.to_csv(PROC / "ipc_dane_mensual.csv", index=False)
    return s


if __name__ == "__main__":
    d = pd.read_csv(PROC / "adres_ejecucion_rubros_mensual.csv", dtype={"codigo": str})
    partes = []
    for (per, tipo, med), g in d.groupby(["periodo", "tipo", "medida"]):
        h = hojas(g).copy()
        h[["categoria", "subcategoria"]] = [clasificar(tipo, c) for c in h["concepto"]]
        h["situacion_fondos"] = h["concepto"].map(situacion)
        partes.append(h)
    hj = pd.concat(partes)

    # control: la suma de hojas debe igualar el total de nivel 1 (sin disponibilidad final)
    ctl = []
    for (per, tipo, med), g in d.groupby(["periodo", "tipo", "medida"]):
        cods = set(g["codigo"])
        raiz = g[[not any(c != o and c.startswith(o + "-") for o in cods) for c in g["codigo"]]]
        tot = raiz["mes"].sum()
        sh = hj[(hj.periodo == per) & (hj.tipo == tipo) & (hj.medida == med)]["mes"].sum()
        ctl.append((per, tipo, med, tot, sh))
    ctl = pd.DataFrame(ctl, columns=["periodo", "tipo", "medida", "total_nivel1", "suma_hojas"])
    ctl["diferencia"] = ctl["total_nivel1"] - ctl["suma_hojas"]
    ctl.to_csv(PROC / "adres_control_hojas_vs_total.csv", index=False)

    s = ipc().set_index("periodo")["ipc"]
    hj["ipc"] = hj["periodo"].map(s)
    factor = s[BASE_IPC] / hj["ipc"]
    agg = (hj.assign(valor_mes_corriente=hj["mes"], valor_mes_constante=hj["mes"] * factor)
             .groupby(["periodo", "tipo", "medida", "categoria", "subcategoria", "situacion_fondos"], dropna=False)
             [["valor_mes_corriente", "valor_mes_constante"]].sum().reset_index())
    agg["base_precios_constantes"] = f"IPC DANE {BASE_IPC}"
    agg["grupo_empalme"] = agg["categoria"].map(GRUPO_EMPALME).fillna(agg["categoria"])
    ref = pd.DataFrame([dict(prioridad=i + 1, tipo=t, categoria=c, subcategoria=sb, patron_concepto=rx,
                             grupo_empalme=GRUPO_EMPALME.get(c, c), justificacion=JUSTIFICACION.get(c, ""))
                        for i, (t, c, sb, rx) in enumerate(REGLAS)])
    (RAIZ / "data" / "reference").mkdir(exist_ok=True)
    ref.to_csv(RAIZ / "data" / "reference" / "adres_clasificacion_rubros.csv", index=False, encoding="utf-8")
    agg.to_csv(PROC / "adres_ejecucion_categorias_mensual.csv", index=False, encoding="utf-8")

    nc = (hj[hj["categoria"] == "Otros sin clasificar"]
          .groupby(["tipo", "concepto"])["mes"].sum().abs().sort_values(ascending=False).reset_index())
    nc.to_csv(PROC / "adres_hojas_no_clasificadas.csv", index=False)
    print("Control (máx |dif| en miles de millones):", (ctl["diferencia"].abs().max() / 1e9).round(2))
    print(ctl.assign(d=ctl.diferencia.abs()).sort_values("d", ascending=False).head(6).to_string())
    print("No clasificado (billones):", (nc["mes"].sum() / 1e12).round(3))
    print(nc.head(30).to_string())
