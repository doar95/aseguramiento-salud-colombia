# Metodología

Versión 0.1 · 15 de octubre de 2026 · Sin revisión por pares

## 1. Qué se quiere medir

El objetivo del repositorio es tener, con datos públicos y replicables, el número de afiliados
al Sistema General de Seguridad Social en Salud (SGSSS) por **EPS, municipio, grupo etario,
sexo, régimen y mes**, y los **parámetros de la Unidad de Pago por Capitación (UPC)** de cada
vigencia. Con ambos se pueden aproximar los procesos de compensación (régimen contributivo) y de
Liquidación Mensual de Afiliados – LMA (régimen subsidiado).

Ninguna fuente pública trae hoy todas esas variables cruzadas y con historia. Los cubos BDUA
de SISPRO sí lo permitían, pero requieren usuario institucional. Por eso el repositorio combina
cuatro fuentes. Cada una cubre una parte:

| Fuente | EPS | Municipio | Edad | Sexo | Régimen | Zona | Periodo |
|---|---|---|---|---|---|---|---|
| SISPRO – extracto del cubo BDUA (Power BI) | no | sí | no | no | sí | no | dic. 2009 – ago. 2026, mensual |
| MinSalud – Cifras de afiliación (ZIP/Excel) | nombre | sí | quinquenios, solo por **departamento** | sí (por depto.) | sí | no | jul. 2025 – sep. 2026, mensual |
| MinSalud – tablero Power BI (tabla con código EPS) | código | sí | no | no | sí | no | dic. 2024, dic. 2025, jul.–sep. 2026 |
| ADRES – datos.gov.co (BDUA) | código | sí | **grupos UPC** | sí | C y S | sí | solo el corte vigente (sep. 2026) |

La única fuente pública con EPS × municipio × grupo etario UPC × sexo × zona es la de la ADRES
en datos.gov.co, pero publica solo la foto del mes vigente y la sobrescribe cada mes. Por eso
este repositorio la **archiva mes a mes** (`data/raw/adres_datos_abiertos/corte-AAAA-MM/`). Desde
septiembre de 2026 en adelante, la serie con todas las dimensiones se irá construyendo sola.

## 2. Definiciones

- **Afiliado vigente**: registro en estado Activo, Activo por emergencia, Protección laboral,
  Suspendido, Suspendido por documento o Suspendido por mora. Se excluyen Retirado, Afiliado
  fallecido, Desafiliado y Afiliación interrumpida, que el cubo de SISPRO conserva como histórico.
  Con esta definición, la serie de SISPRO coincide **exactamente** con los totales que publica
  MinSalud en los 14 meses en que ambas fuentes se superponen (julio de 2025 a agosto de 2026),
  tanto en el total como en contributivo y subsidiado.
- **Activo por emergencia**: estado que aparece entre julio de 2020 y agosto de 2022, sobre todo
  en el régimen contributivo (protección durante la emergencia por COVID-19). Se cuenta como
  vigente. La columna `total_solo_activos` permite excluirlo.
- **Grupos etarios UPC**: menores de 1 año; 1-4; 5-14; 15-18 hombres; 15-18 mujeres;
  19-44 hombres; 19-44 mujeres; 45-49; 50-54; 55-59; 60-64; 65-69; 70-74; 75 y más.
  La ADRES publica los rangos como "1 a 5", "19 a 45", etc. Se interpretan como los grupos de la
  resolución (límite superior abierto).
- **Código de municipio**: código DIVIPOLA del DANE de 5 dígitos. Cuando la fuente solo trae el
  nombre (MinSalud de julio a diciembre de 2025; ADRES), se asigna por nombre con la geografía del
  propio cubo SISPRO y una tabla de equivalencias para nombres abreviados de la BDUA
  (`scripts/comun.py`). Todos los registros quedaron con código.
- **EPS**: los libros de MinSalud agrupan por nombre corto (p. ej., "NUEVA EPS" suma los códigos
  EPS037 y EPSS41). La ADRES y el tablero Power BI conservan el código de habilitación. Para
  compensación y LMA debe usarse el código.

## 3. Parámetros de la UPC

`data/processed/upc_valor_base_anual.csv` trae la UPC anual base (zona normal) de cada régimen
entre 2013 y 2026. `upc_estructura_costo_grupo_etario.csv` trae la estructura de costo
(ponderador) de los 14 grupos.

- Régimen contributivo: una estructura entre 2013 y 2022, y otra desde 2023. En 2022 conviven
  las dos, porque la resolución fija un valor con la estructura anterior y otro, mayor, que
  incluye las tecnologías de la Resolución 2292 de 2021 con la nueva.
- Régimen subsidiado: la misma estructura en todas las vigencias de 2013 a 2026.
- Verificación: nueve resoluciones tienen texto digital y los valores se leyeron del PDF. Cinco
  (2013, 2014, 2015, 2018 y 2021) son escaneos: se pasaron por OCR en español y las tablas de
  2014 y 2018 se revisaron además contra la imagen de la página. La columna `verificacion` lo indica.

**Pendiente:** primas por zona especial de dispersión geográfica, ciudades y San Andrés, con
sus anexos de municipios por vigencia; prima por concentración de riesgo etario por EPS; UPC
diferencial indígena; y los ajustes que se expidieron durante algunas vigencias (p. ej., 2024
y 2025). Son necesarios para que la simulación por municipio refleje la UPC realmente aplicable.

## 4. UPC teórica (ejercicio ilustrativo)

`adres_upc_teorica_eps_municipio_AAAA-MM.csv` multiplica los afiliados de cada EPS y municipio
por la estructura de costo de su grupo etario y por la UPC base de la vigencia:

    UPC teórica anual = Σ_grupos afiliados_g × ponderador_g × UPC_base

No es una estimación de lo girado. Usa siempre la zona normal y no aplica primas por
dispersión, ciudades, concentración de riesgo etario ni UPC indígena. Tampoco considera los días
compensados o liquidados, las novedades ni las restituciones. Sirve para comparar EPS y
municipios en una misma escala y para ver el efecto del envejecimiento: el ponderador promedio
de septiembre de 2026 es 1,25 en el contributivo y 1,15 en el subsidiado.

## 5. Vacíos conocidos

- El extracto de SISPRO no tiene los meses de enero a octubre de 2010, enero de 2011 ni enero
  a marzo de 2012.
- No hay EPS × municipio × grupo etario con historia. Para reconstruirlo hace falta el acceso a
  los cubos BDUA de SISPRO o una solicitud de información a la ADRES o a MinSalud.
- El tablero histórico de MinSalud en Tableau Public (diciembre de 2018 a junio de 2025)
  rechazó las consultas automatizadas. Puede intentarse manualmente desde el navegador.
- La ADRES publica en `datos.gov.co` muchas "vistas" filtradas por municipio. No son fuentes
  distintas: son subconjuntos de los dos conjuntos nacionales que se usan aquí.

## 6. Uso de inteligencia artificial

La búsqueda de fuentes, la descarga, el OCR, la transcripción de parámetros y los scripts los
hizo Claude (Anthropic) a pedido de David Aguilar. Los totales se validaron cruzando fuentes
independientes (sección 2) y los parámetros de la UPC contra el texto o la imagen de cada
resolución (sección 3). Antes de usar cifras para decisiones, revise los valores directamente
en la norma citada.
