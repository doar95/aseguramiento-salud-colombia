# Afiliación en salud en Colombia: afiliados por EPS, municipio, edad y régimen, y parámetros de la UPC

Este repositorio reúne datos públicos de afiliación al Sistema General de Seguridad Social en
Salud (SGSSS) y los parámetros de la Unidad de Pago por Capitación (UPC). Todo es replicable con
fuentes oficiales.

El objetivo de largo plazo es mostrar en un mapa municipal cómo han cambiado en los últimos años
los afiliados y los ponderadores de la UPC, y aproximar con datos abiertos la compensación del
régimen contributivo y la Liquidación Mensual de Afiliados (LMA) del régimen subsidiado.

> Versión 0.1 · 15 de octubre de 2026 · Proyecto independiente, sin revisión por pares.

## Qué hay

| Tabla (en `data/processed/`) | Nivel | Periodo |
|---|---|---|
| `sispro_afiliados_activos_municipio_mensual.csv` | municipio × régimen × mes | dic. 2009 – ago. 2026 (187 meses) |
| `minsalud_eps_municipio_regimen_mensual.csv` | EPS × municipio × régimen × mes | jul. 2025 – sep. 2026 |
| `minsalud_cobertura_municipio_mensual.csv` | municipio × mes, con población DANE y cobertura | jul. 2025 – sep. 2026 |
| `minsalud_eps_depto_regimen_quinquenio_sexo.csv` | EPS × departamento × régimen × quinquenio × sexo × mes | jul. 2025 – sep. 2026 |
| `adres_bdua_eps_municipio_sexo_grupo_upc_2026-09.csv.gz` | código EPS × municipio × sexo × **grupo etario UPC** × zona | corte sep. 2026 |
| `adres_upc_teorica_eps_municipio_2026-09.csv` | EPS × municipio: UPC teórica (ilustrativa) | corte sep. 2026 |
| `upc_valor_base_anual.csv` | UPC-C y UPC-S por vigencia | 2013 – 2026 |
| `upc_estructura_costo_grupo_etario.csv` | ponderadores de los 14 grupos etarios | 2013 – 2026 |

Los archivos crudos, tal como se descargaron, están en `data/raw/`. Las 14 resoluciones anuales
de la UPC (2013 a 2026) están en `normativa/upc/`.

**Validación:** la serie de SISPRO y los archivos de MinSalud coinciden exactamente, en total,
contributivo y subsidiado, en los 14 meses en que se superponen.

## Qué falta

No hay una fuente pública con **EPS × municipio × grupo etario con historia**. La más cercana es la
BDUA de la ADRES en datos.gov.co, que trae todas esas dimensiones pero solo para el mes vigente.
Por eso el repositorio guarda una copia cada mes. Para reconstruir los años anteriores hace falta
el acceso a los cubos BDUA de SISPRO o una solicitud de información.

Lo que sigue pendiente está en [docs/metodologia.md](docs/metodologia.md): primas por zona y sus
anexos de municipios, prima por concentración etaria, UPC indígena y el mapa interactivo.

## Cómo actualizar

```bash
pip install -r requirements.txt
python scripts/00_descargar_fuentes.py todo   # baja los meses nuevos (MinSalud, ADRES, SISPRO, UPC)
python scripts/01_minsalud_cifras.py
python scripts/02_sispro_cubo_bdua.py
python scripts/03_upc_parametros.py
python scripts/04_adres_bdua_upc.py 2026-09   # use el corte que corresponda
```

Si un portal bloquea la descarga automática, baje el archivo con el navegador y guárdelo en la
carpeta de `data/raw/` correspondiente, con el nombre que usa el script.

## Estructura

```
data/raw/minsalud_cifras_afiliacion/   ZIP mensuales de MinSalud (+ manuales del tablero)
data/raw/minsalud_tablero_powerbi/     tabla EPS (código) × municipio y catálogo de EPS
data/raw/sispro_cubo_bdua/             extracto mensual del cubo BDUA (SISPRO) y geografía
data/raw/adres_datos_abiertos/         fotos mensuales de la BDUA (ADRES, datos.gov.co)
data/processed/                        tablas limpias en formato largo (CSV, UTF-8)
normativa/upc/                         resoluciones de UPC por vigencia (PDF originales)
scripts/                               descarga y procesamiento (Python)
docs/                                  metodología y fuentes (ICONTEC y APA)
```

## Fuentes

- Ministerio de Salud y Protección Social: *Cifras de afiliación en salud* y *Construya su
  consulta – Aseguramiento* (SISPRO).
- ADRES: *Población Base de Datos Única de Afiliados BDUA* de los regímenes contributivo y
  subsidiado (datos.gov.co, CC BY-SA 4.0).
- Ministerio de Salud y Protección Social: resoluciones anuales que fijan la UPC (2012 a 2025).

Las referencias completas, en formato ICONTEC (NTC 5613) y APA, están en
[docs/fuentes.md](docs/fuentes.md). La versión legible por máquina está en `docs/fuentes.json`.

## Licencia

- Código (`scripts/`): MIT.
- Datos derivados de la ADRES (datos.gov.co): CC BY-SA 4.0, la misma licencia de la fuente.
- Demás datos y normas: información pública reutilizable según la Ley 1712 de 2014, citando
  la fuente oficial.

## Cómo citar

Claude (Anthropic) y Aguilar, D. (2026). *Afiliación en salud en Colombia: afiliados por EPS,
municipio, edad y régimen, y parámetros de la UPC* (versión 0.1) [Repositorio de datos].
GitHub. https://github.com/doar95/afiliacion-salud-colombia

Claude figura como autor para dejar trazabilidad de su participación en la búsqueda,
descarga y procesamiento de los datos. Ver la sección 6 de la metodología.
