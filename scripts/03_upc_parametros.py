"""
Tablas de parámetros de la UPC transcritas de las resoluciones anuales del
Ministerio de Salud y Protección Social (carpeta normativa/upc/).

Salidas:
  data/processed/upc_valor_base_anual.csv           (UPC-C y UPC-S base por vigencia)
  data/processed/upc_estructura_costo_grupo_etario.csv (ponderadores por grupo etario)

Cada valor se transcribió del artículo 1 (UPC-C) y del artículo de la UPC-S de la
resolución correspondiente y se verificó contra el texto extraído del PDF (o contra
la imagen de la página, en las resoluciones escaneadas). Ver docs/metodologia.md.

Uso: python scripts/03_upc_parametros.py
"""
from pathlib import Path
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
OUT = RAIZ / "data" / "processed"
OUT.mkdir(parents=True, exist_ok=True)

# vigencia, resolución, fecha, UPC-C anual, UPC-S anual, verificación, nota
BASE = [
    (2013, "Resolución 4480 de 2012", "2012-12-27", 568944.00, 508993.20, "OCR + revisión visual", ""),
    (2014, "Resolución 5522 de 2013", "2013-12-27", 593978.40, 531388.80, "OCR + revisión visual", ""),
    (2015, "Resolución 5925 de 2014", "2014-12-23", 629974.80, 563590.80, "OCR", ""),
    (2016, "Resolución 5593 de 2015", "2015-12-24", 689508.00, 616849.20, "texto PDF", ""),
    (2017, "Resolución 6411 de 2016", "2016-12-26", 746046.00, 667429.20, "texto PDF", ""),
    (2018, "Resolución 5268 de 2017", "2017-12-22", 804463.20, 719690.40, "OCR + revisión visual", ""),
    (2019, "Resolución 5858 de 2018", "2018-12-26", 847180.80, 787327.20, "texto PDF", ""),
    (2020, "Resolución 3513 de 2019", "2019-12-26", 892591.20, 829526.40, "texto PDF", ""),
    (2021, "Resolución 2503 de 2020", "2020-12-28", 938826.00, 872496.00, "OCR", ""),
    (2022, "Resolución 2381 de 2021", "2021-12-28", 989712.00, 927723.60, "texto PDF",
     "Valor por tecnologías que se venían financiando. Con la inclusión de la Res. 2292 de 2021 "
     "la UPC a reconocer fue UPC-C $1.109.221,20 y UPC-S $964.807,20 (estructura de costo nueva en UPC-C)."),
    (2023, "Resolución 2809 de 2022", "2022-12-30", 1289246.40, 1121396.40, "texto PDF", ""),
    (2024, "Resolución 2364 de 2023", "2023-12-29", 1444086.00, 1256076.00, "texto PDF",
     "Revisar ajustes posteriores expedidos durante la vigencia."),
    (2025, "Resolución 2717 de 2024", "2024-12-30", 1521489.60, 1323403.20, "texto PDF",
     "Revisar ajustes posteriores expedidos durante la vigencia."),
    (2026, "Resolución 2764 de 2025", "2025-12-30", 1658912.01, 1541706.27, "texto PDF",
     "La UPC-S incorpora la equiparación de la Res. 2605 de 2025 (Auto 2049 de 2025)."),
]
GRUPOS = ["Menores de 1 año", "1-4 años", "5-14 años", "15-18 años hombres", "15-18 años mujeres",
          "19-44 años hombres", "19-44 años mujeres", "45-49 años", "50-54 años", "55-59 años",
          "60-64 años", "65-69 años", "70-74 años", "75 años y más"]
CLAVE = ["<1", "1-4", "5-14", "15-18H", "15-18M", "19-44H", "19-44M", "45-49", "50-54", "55-59",
         "60-64", "65-69", "70-74", "75+"]
C_ANTES = [2.9679, 0.9530, 0.3329, 0.3173, 0.5014, 0.5646, 1.0475, 1.0361, 1.3215, 1.6154,
           2.0790, 2.5861, 3.1033, 3.8997]
C_2023 = [2.9966, 0.8618, 0.3475, 0.3354, 0.5262, 0.5785, 1.0683, 1.0902, 1.3796, 1.6332,
          2.0971, 2.5977, 3.1411, 3.9188]
S_TODOS = [2.7654, 0.8179, 0.3267, 0.3847, 0.6381, 0.6415, 1.0154, 1.0376, 1.2973, 1.5738,
           1.9465, 2.4125, 2.9424, 3.6575]

base = pd.DataFrame(BASE, columns=["vigencia", "resolucion", "fecha_expedicion", "upc_c_anual",
                                   "upc_s_anual", "verificacion", "nota"])
base["upc_c_diaria"] = (base["upc_c_anual"] / 360).round(2)
base["upc_s_diaria"] = (base["upc_s_anual"] / 360).round(2)
base["razon_s_c"] = (base["upc_s_anual"] / base["upc_c_anual"]).round(4)
base.to_csv(OUT / "upc_valor_base_anual.csv", index=False, encoding="utf-8")

filas = []
for _, r in base.iterrows():
    y = r["vigencia"]
    pc = C_2023 if y >= 2023 else C_ANTES
    for g, k, wc, ws in zip(GRUPOS, CLAVE, pc, S_TODOS):
        filas.append((y, r["resolucion"], "contributivo", k, g, wc, round(wc * r["upc_c_anual"], 2)))
        filas.append((y, r["resolucion"], "subsidiado", k, g, ws, round(ws * r["upc_s_anual"], 2)))
pond = pd.DataFrame(filas, columns=["vigencia", "resolucion", "regimen", "grupo_clave", "grupo_etario",
                                    "estructura_costo", "valor_anual_zona_normal"])
pond.to_csv(OUT / "upc_estructura_costo_grupo_etario.csv", index=False, encoding="utf-8")
print(base[["vigencia", "upc_c_anual", "upc_s_anual", "razon_s_c"]].to_string(index=False))
print(pond.shape)
