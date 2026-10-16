# Guía para descargar los datos

Hay dos caminos: usar las tablas ya procesadas de este repositorio o bajar los insumos de cada
entidad y reproducir el proceso.

## 1. Usar las tablas procesadas

1. Entre a https://github.com/doar95/aseguramiento-salud-colombia y abra la carpeta
   `data/processed/`.
2. Haga clic en el archivo y luego en el botón de descarga (*Download raw file*).
3. Ábralo en Excel: *Datos → Obtener datos → Desde texto/CSV*, con origen **65001: Unicode (UTF-8)**
   y delimitador **coma**. Así se conservan las tildes y los códigos DANE con cero inicial
   (por ejemplo, `05001`).
4. Los archivos `.csv.gz` están comprimidos. Descomprímalos con 7-Zip o léalos en Python con
   `pandas.read_csv("archivo.csv.gz")`.

Para bajar todo: botón verde *Code → Download ZIP*.

## 2. Bajar los insumos de cada entidad

| Insumo | Dónde está | Carpeta del repositorio | Script |
|---|---|---|---|
| Cifras de afiliación (ZIP mensuales) | Ministerio de Salud, *Cifras de aseguramiento en salud* | `data/raw/minsalud_cifras_afiliacion/` | `00 minsalud` |
| Cubo BDUA (afiliados por municipio, régimen y estado) | SISPRO, *Construya su consulta – Aseguramiento* (tablero Power BI público) | `data/raw/sispro_cubo_bdua/` | `00 sispro` |
| BDUA contributivo y subsidiado (EPS, municipio, sexo, edad) | datos.gov.co, conjuntos `tq4m-hmg2` y `d7a5-cnra` (ADRES) | `data/raw/adres_datos_abiertos/corte-AAAA-MM/` | `00 adres` |
| Resoluciones de UPC | Normatividad del Ministerio de Salud (enlaces en `docs/fuentes.json`) | `normativa/upc/` | `00 upc` |
| Ejecución presupuestal mensual | adres.gov.co → Nuestra entidad → Información financiera → Unidad de Recursos Administrados → Presupuesto | `data/raw/adres_ejecucion/adres_ejecucion_AAAA-MM.xls[x]` | manual |
| Proyecciones de población municipal por área, sexo y edad 2018–2042 y retroproyecciones 2005–2017 | DANE → Estadísticas por tema → Demografía y población → [Proyecciones de población](https://www.dane.gov.co/index.php/estadisticas-por-tema/demografia-y-poblacion/proyecciones-de-poblacion) | `data/raw/dane/` (no se versionan: 131 MB y 56 MB) | manual |
| DIVIPOLA y Marco Geoestadístico Nacional (MGN) | Geoportal del DANE | `data/raw/dane/` | manual |
| IPC (índices mensuales) | DANE → Precios y costos → Índice de precios al consumidor | `data/raw/dane/` | manual |
| Autos de la Corte Constitucional | Relatoría de la Corte (enlaces en `data/reference/corte_constitucional_autos.csv`) | — | — |

Los archivos de la ADRES y del DANE marcados como «manual» se bajan con el navegador. Los
portales a veces bloquean la descarga automática o cambian la dirección de los archivos. Guarde
cada archivo con el nombre que espera el script; el nombre está en el encabezado de cada script.

**Ejecución de la ADRES:** el nombre que trae el archivo no siempre coincide con su mes. El script
`06_adres_ejecucion.py` toma el periodo del encabezado de la hoja de ingresos («Ingresos desde
01/MM/AAAA»), no del nombre.

## 3. Reproducir

```bash
pip install -r requirements.txt
python scripts/00_descargar_fuentes.py todo
python scripts/01_minsalud_cifras.py
python scripts/02_sispro_cubo_bdua.py
python scripts/03_upc_parametros.py
python scripts/05_dane_poblacion.py
python scripts/06_adres_ejecucion.py
python scripts/07_adres_clasificacion.py
python scripts/08_upc_zonas.py
python scripts/04_adres_bdua_upc.py 2026-09
python scripts/09_territorio.py
python scripts/10_datos_sitio.py
```

## 4. Si algo no cuadra

Abra un *issue* en el repositorio con el archivo, la fila y la fuente oficial con la que lo
comparó. Las correcciones se documentan en el historial de cambios.
