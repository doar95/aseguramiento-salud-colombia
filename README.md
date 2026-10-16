# Aseguramiento en salud en Colombia, 2013–2026

**Afiliación por municipio · UPC y sus zonas · finanzas de la ADRES · seguimiento de la Corte Constitucional**

Sitio con el documento y el tablero: **https://doar95.github.io/aseguramiento-salud-colombia/**

Este repositorio reúne datos públicos del Sistema General de Seguridad Social en Salud (SGSSS),
los limpia y los deja listos para descargar, con el código para reproducir cada paso. Está pensado
para servidores públicos, investigadores y ciudadanos que no necesariamente conocen el sistema.

> Versión 1.0 · octubre de 2026 · Proyecto independiente, sin revisión por pares.
> Autores: Claude (Anthropic), David Aguilar y Camila Gómez.
> El mérito es de las entidades que publican datos abiertos: Ministerio de Salud y Protección
> Social, ADRES, SISPRO, DANE, Corte Constitucional y DNP.

## Antes de usar estas cifras

- Los afiliados se cuentan en el **municipio de afiliación** que registra la BDUA. No siempre es
  el municipio donde la persona vive o se atiende.
- Este repositorio **no reemplaza** la Liquidación Mensual de Afiliados (LMA) del régimen
  subsidiado, el proceso de compensación del contributivo ni las cifras oficiales de las entidades.
- **No se reparten afiliados por edad cuando no hay distribución por edad.** La única fuente
  pública por municipio y edad es el corte vigente de la BDUA de la ADRES. Las series históricas por
  edad quedan pendientes hasta recuperar el acceso a los cubos de la BDUA en SISPRO.

## Glosario mínimo

| Término | Qué es |
|---|---|
| SGSSS | Sistema General de Seguridad Social en Salud |
| Régimen contributivo | Personas con capacidad de pago (asalariados, independientes) y sus beneficiarios; se financia con cotizaciones |
| Régimen subsidiado | Población sin capacidad de pago; se financia con recursos públicos (Nación, SGP, departamentos y municipios) |
| EPS | Entidad Promotora de Salud: la aseguradora a la que se afilia la persona |
| BDUA | Base de Datos Única de Afiliados, que opera la ADRES |
| ADRES | Administradora de los Recursos del SGSSS: recibe los recursos y paga a las EPS |
| UPC | Unidad de Pago por Capitación: lo que la ADRES reconoce a la EPS por cada afiliado al año. Se ajusta por edad, sexo y zona |
| Ponderador o estructura de costo | Multiplicador de la UPC según el grupo de edad y sexo |
| Presupuestos máximos | Desde 2020, techo anual que la ADRES gira a las EPS para servicios no financiados con la UPC (antes se pagaban por recobro) |

## Qué hay

| Módulo | Tabla en `data/processed/` | Nivel | Periodo |
|---|---|---|---|
| Afiliación | `sispro_afiliados_activos_municipio_mensual.csv` | municipio × régimen × mes | dic. 2009 – ago. 2026 |
| | `minsalud_eps_municipio_regimen_mensual.csv` | EPS × municipio × régimen × mes | jul. 2025 – sep. 2026 |
| | `minsalud_cobertura_municipio_mensual.csv` | municipio × mes, con población DANE | jul. 2025 – sep. 2026 |
| | `minsalud_eps_depto_regimen_quinquenio_sexo.csv` | EPS × departamento × régimen × edad quinquenal × sexo | jul. 2025 – sep. 2026 |
| | `adres_bdua_eps_municipio_sexo_grupo_upc_AAAA-MM.csv.gz` | EPS × municipio × sexo × grupo de edad UPC | un corte por mes (se acumulan) |
| UPC | `upc_valor_base_anual.csv` | UPC-C y UPC-S por vigencia | 2013 – 2026 |
| | `upc_estructura_costo_grupo_etario.csv` | 14 grupos de edad × régimen | 2013 – 2026 |
| | `upc_valores_por_articulo.csv` | cada tabla etaria de cada resolución → UPC implícita | 2013 – 2026 |
| | `upc_primas_zona.csv` | vigencia × régimen × variante × zona: prima y UPC | 2013 – 2026 |
| | `upc_municipio_zona.csv` | vigencia × régimen × municipio → zona, **con columna de verificación** | 2013 – 2026 |
| | `upc_prima_etaria_eps.csv` | prima por concentración de riesgo etario por EPS | 2013 – 2026 |
| Población | `dane_poblacion_municipio_grupo_upc.csv`, `dane_poblacion_municipio_total.csv` | municipio × año × grupo UPC | 2013 – 2030 |
| Territorio | `municipios_atributos.csv` | DIVIPOLA, ruralidad, altitud, clima | — |
| Finanzas | `adres_ejecucion_rubros_mensual.csv` | rubro × mes (ingresos y gastos) | ago. 2017 – sep. 2026 |
| | `adres_ejecucion_categorias_mensual.csv` | categoría comparable × mes, corrientes y constantes | ago. 2017 – sep. 2026 |
| | `ipc_dane_mensual.csv` | IPC | — |
| Corte | `data/reference/corte_constitucional_autos.csv` | autos sobre UPC y presupuestos máximos | 2023 – 2025 |

Los insumos están en `data/raw/`, las 14 resoluciones de la UPC en `normativa/upc/` (PDF y texto
extraído) y las reglas de clasificación de la ADRES, con su justificación, en
`data/reference/adres_clasificacion_rubros.csv`.

## Hallazgos que conviene conocer

- Los totales de afiliados de SISPRO y de MinSalud coinciden exactamente en los 14 meses en que se
  superponen.
- Cada prima de la UPC se comprobó contra las tablas por edad de la resolución. En el subsidiado,
  San Andrés tiene un valor fijo desde 2019; Guainía tiene una prima de 17,81 % desde 2023. En
  2016–2018 Bogotá, Medellín, Cali y Barranquilla tuvieron una UPC-S de prueba piloto (igualación
  de prima pura) y por eso no aparecen en la lista de ciudades del subsidiado esos años.
- La lista de municipios con prima por dispersión geográfica tiene 363 filas de 2014 a 2022.
- El gasto no financiado con la UPC se presenta como una serie empalmada: recobros hasta 2019 y
  presupuestos máximos desde 2020. Antes de 2020 el no UPC del subsidiado no pasa por la ADRES.

## Cómo reproducir

```bash
pip install -r requirements.txt
python scripts/00_descargar_fuentes.py todo     # MinSalud, ADRES, SISPRO, resoluciones UPC
python scripts/01_minsalud_cifras.py
python scripts/02_sispro_cubo_bdua.py
python scripts/03_upc_parametros.py
python scripts/05_dane_poblacion.py              # requiere los libros del DANE (ver guía)
python scripts/06_adres_ejecucion.py
python scripts/07_adres_clasificacion.py
python scripts/08_upc_zonas.py
python scripts/04_adres_bdua_upc.py 2026-09      # corte de la BDUA de la ADRES
python scripts/09_territorio.py
python scripts/10_datos_sitio.py                 # JSON del tablero en docs/data/
```

La guía de descarga, con la ruta de cada archivo en las páginas de las entidades, está en
[docs/guia_descarga.md](docs/guia_descarga.md).

## Actualización mensual

Un flujo de GitHub Actions (`.github/workflows/actualizacion_mensual.yml`) corre el día 20 de cada
mes. Descarga el corte nuevo de la BDUA de la ADRES, lo procesa, regenera los datos del sitio y
guarda los cambios. Si algo falla, abre un *issue* en el repositorio; GitHub envía un correo al
dueño. Si todo sale bien no se envía nada.

## Estructura

```
data/raw/                 insumos tal como se descargaron (salvo los libros grandes del DANE)
data/processed/           tablas limpias (CSV, UTF-8, separador coma)
data/reference/           reglas, listas OCR, autos de la Corte
normativa/upc/            resoluciones de la UPC (PDF) y su texto extraído
scripts/                  descarga y procesamiento, numerados en orden
docs/                     sitio web (index.html), metodología, fuentes y guía
```

## Fuentes, licencia y cita

Las referencias completas, en formato ICONTEC (NTC 5613) y APA, están en
[docs/fuentes.md](docs/fuentes.md).

- Código: licencia MIT.
- Datos derivados de la ADRES (datos.gov.co): CC BY-SA 4.0, la misma licencia de la fuente.
- Demás datos y normas: información pública reutilizable según la Ley 1712 de 2014, citando la
  fuente oficial.
- Bases de altitud, clima y ruralidad 2018: aportadas por los coautores (`data/raw/base_interna/`).
  Ver [docs/fuentes.md](docs/fuentes.md).

**Cómo citar:** Claude (Anthropic), Aguilar, D. y Gómez, C. (2026). *Aseguramiento en salud en
Colombia, 2013–2026: afiliación por municipio, UPC y sus zonas, finanzas de la ADRES y seguimiento
judicial* (versión 1.0) [Repositorio de datos y código]. GitHub.
https://github.com/doar95/aseguramiento-salud-colombia

Claude figura como autor para dejar trazabilidad de su participación en la búsqueda, descarga,
procesamiento y redacción. Ver la sección «Uso de inteligencia artificial» de la metodología.
