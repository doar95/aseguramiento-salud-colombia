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

### 3.1 Primas por zona y municipios (`scripts/08_upc_zonas.py`)

**Comprobación de cada valor.** Cada artículo que fija una UPC trae una tabla por grupo de edad.
Al dividir el valor del grupo «menores de un año» entre su ponderador se obtiene la UPC anual de
ese artículo. `upc_valores_por_articulo.csv` guarda esa UPC implícita y su razón frente a la UPC
base. La prima escrita en el texto se acepta solo si coincide con esa razón; la columna `metodo`
de `upc_primas_zona.csv` lo dice.

| Zona | Contributivo | Subsidiado |
|---|---|---|
| Dispersión geográfica | 10 % | 11,47 % |
| Ciudades | 9,85 % (2013), 9,86 % (2014–2026) | 15 % |
| San Andrés (zona alejada) | 37,9 % desde 2015 (2013–2014: en la lista de ciudades) | 37,9 % en 2015–2018; desde 2019 un valor fijo: 1,4516 × UPC-S (2019–2022 y 2026) y 1,5509 × UPC-S (2023–2025) |
| Guainía | — | 17,81 % desde 2023 |
| UPC diferencial indígena (EPSI) | — | +3,04 % (2015–2016); +4,81 % desde 2017; sobre ella se aplican las primas de dispersión y ciudades |
| Prueba piloto de igualación de prima pura | — | Bogotá, Medellín, Cali y Barranquilla, 2016–2018 (1,2013 × UPC-S) |
| 2022, «con nuevas inclusiones» (Res. 2292 de 2021) | 1,1208 × UPC-C base y sus primas | 1,0400 × UPC-S base y sus primas |

**Municipios.** Las listas de dispersión se leen de los anexos (código DANE y nombre). Si el código
impreso no existe se busca el nombre dentro del departamento. En los años escaneados (2014, 2015,
2018 y 2021) se borraron las líneas de la tabla de la imagen y se aplicó OCR solo a las columnas de
número y código (`data/reference/upc_anexos_ocr/`). Un código ilegible se corrige solo si difiere
en un dígito de un único código válido de las listas vecinas, y el orden de la tabla desempata.
Una fila que el OCR no logró leer se incluye solo si el anexo tiene 363 filas, como las vigencias
vecinas, y todas las filas leídas coinciden. Las filas revisadas sobre la imagen se marcan
«verificada visualmente».

- 2013 no tiene anexo. La prima se define para los departamentos de Amazonas, Arauca, Casanare,
  Caquetá, Chocó, Guajira, Guainía, Guaviare, Meta, Putumayo, Sucre, Vaupés y Vichada, y para «la
  región de Urabá». Se exceptúan Arauca, Florencia y Yopal «con sus respectivas áreas de
  influencia», que la resolución no delimita. Urabá se interpretó como los 11 municipios de la
  subregión Urabá antioqueño. Ambas decisiones quedan marcadas en la columna `verificacion`.
- Cuando un municipio figura en dos listas se asigna una sola zona, por precedencia: San Andrés,
  Guainía, ciudades piloto, ciudades y dispersión. Por ejemplo, Villavicencio en 2013. Queda marcado.
- 2022: el código de Miraflores (Guaviare) es ilegible en el PDF («ozuu»); la fila 353 lo nombra.
- Ciudades: hasta 2025 se leen del artículo; en 2026, del Anexo 2.

**Prima por concentración de riesgo etario** (Acuerdo 026 de 2011 de la CRES): por EPS y
vigencia, en `upc_prima_etaria_eps.csv`.

**Pendiente:** los ajustes de la UPC que se expidieron durante algunas vigencias, después de la
resolución anual, no están incorporados.

## 4. UPC teórica (ejercicio ilustrativo)

`adres_upc_teorica_eps_municipio_AAAA-MM.csv` multiplica los afiliados de cada EPS y municipio
por la estructura de costo de su grupo etario y por la UPC base de la vigencia:

    UPC teórica anual = Σ_grupos afiliados_g × ponderador_g × UPC_base

No es una estimación de lo girado. Aplica la prima de la zona del municipio de afiliación, pero no
la de concentración de riesgo etario ni la UPC indígena. Tampoco considera los días
compensados o liquidados, las novedades ni las restituciones. Sirve para comparar EPS y
municipios en una misma escala y para ver el efecto del envejecimiento: el ponderador promedio
de septiembre de 2026 es 1,25 en el contributivo y 1,15 en el subsidiado.

## 5. Población del DANE (`scripts/05_dane_poblacion.py`)

Proyecciones municipales por área, sexo y edad simple (2018–2042, actualización de julio de 2025)
y retroproyecciones 2005–2017. Se usa el total del municipio, sin distinguir área. Las edades
simples se suman en los 14 grupos de la UPC. Sirve como denominador; no se usa para repartir
afiliados por edad.

## 6. Finanzas de la ADRES (`scripts/06` y `07`)

- **Insumo.** Ejecución presupuestal mensual de la Unidad de Recursos Administrados, de agosto de
  2017 (inicio de la ADRES) a septiembre de 2026: 110 libros. Gastos con tres bloques (acumulado
  anterior, mes y acumulado); se usan compromisos (registro presupuestal) y obligaciones.
- **Comparabilidad.** En 2020 los códigos pasaron al Catálogo de Clasificación Presupuestal. Por
  eso se clasifican solo los rubros más desagregados (hojas), por su nombre, con reglas
  ordenadas. Las reglas y su justificación están en `data/reference/adres_clasificacion_rubros.csv`.
  La suma de las hojas reproduce el total de cada mes, con una diferencia máxima de 14,5 mil
  millones (2020). Lo no clasificado queda visible en `adres_hojas_no_clasificadas.csv`.
- **Empalme no UPC.** Recobros (hasta 2019) y presupuestos máximos (desde 2020, art. 240 de la
  Ley 1955 de 2019), con sus ajustes de vigencias anteriores, forman una sola serie
  (`grupo_empalme`). El saneamiento de deudas va aparte porque paga cuentas de años anteriores.
  Hay una ruptura de cobertura: antes de 2020 el no UPC del subsidiado lo pagaban los
  departamentos y no aparece en la ADRES. El art. 231 de la Ley 1955 lo asignó a la Nación desde
  el 1 de enero de 2020; ver también la Resolución 94 de 2020. La caída de 2022 coincide con la UPC
  «con nuevas inclusiones» de la Resolución 2381 de 2021.
- **Situación de fondos.** Parte del gasto se registra sin situación de fondos (SSF), por
  ejemplo la UPC del contributivo hasta 2022 y la cofinanciación territorial del subsidiado. Se
  marca en la columna `situacion_fondos`.
- **Precios constantes.** IPC mensual del DANE, base septiembre de 2026.

## 7. Territorio (`scripts/09_territorio.py`)

DIVIPOLA (junio de 2026), geometría del Marco Geoestadístico Nacional 2024 simplificada para la
web, y tres atributos:

- Altitud y clima: base aportada por los coautores. El archivo cita a la Unidad de Analítica en
  Salud del IETS y al DNP, con base en el «Mapa de Clasificación del Clima en Colombia».
- Ruralidad 2018: base aportada por los coautores, sin fuente en el archivo. Se trata como
  **base interna**. Usa las cuatro categorías de la Misión para la Transformación del Campo
  (DNP), pero difiere en 159 de 1.121 municipios de la categoría que trae la geografía del cubo de SISPRO
  (`ruralidad_sispro`), que también se publica.
- Nuevo Belén de Bajirá (27493) aún no tiene geometría en el MGN 2024. Sus datos están en las
  tablas, pero no aparece en el mapa.

## 8. Corte Constitucional

`data/reference/corte_constitucional_autos.csv` resume la parte resolutiva de cada auto, leída en
el texto oficial de la relatoría. Un «Auto/Resolución 067 de 2025» mencionado en la planeación no
se localizó y no se incluye.

## 9. Liquidación del subsidiado por municipio (`scripts/12_adres_lma_financiacion.py`)

Fuente: ADRES, «Informe de Financiación LMA» (Entidades territoriales → Financiamiento), un libro
acumulado por mes. Se usa el de diciembre de cada año (2020–2025) y el último de 2026 (enero a julio).
De la hoja «FinalTotal» se toman, por municipio: UPC apropiada (A), cajas de compensación (B),
cofinanciación departamental (C), cofinanciación municipal (D) y aportes de la Nación por la ADRES
(A-B-C-D); la identidad se cumple con diferencias de redondeo de 2 pesos. Las filas con código
terminado en 000 son las gobernaciones (áreas no municipalizadas). Total nacional de la UPC
apropiada: 24,58 billones en 2020 y 44,63 en 2025, cerca de las obligaciones de «UPC régimen
subsidiado» de la ejecución de la ADRES (24,35 y 43,43). La «UPC por afiliado» del sitio divide la LMA
anualizada entre los afiliados del subsidiado de diciembre (SISPRO): es una aproximación.

## 10. EPS bajo medida de la Supersalud (`data/reference/eps_medidas_supersalud.csv`)

Tabla revisada a mano. Para cada EPS: códigos de habilitación (todos los de la EPS se afectan
juntos), medida, fecha de inicio, fecha de fin o estado, acto administrativo y enlaces. Se priorizó
la resolución de la Supersalud o la decisión judicial; cuando no se encontró, la noticia que la cita,
y así se indica. Un mes cuenta como intervenido si la medida estuvo vigente algún día de ese mes.
Casos especiales: Sanitas (la SU-277 de 2025 dejó sin efectos la medida; se usa la fecha de la
sentencia), Savia Salud (suspensión provisional judicial en abril de 2026; la entrega no está
confirmada) y Coosalud (suspensión provisional en abril de 2026, pero reportada intervenida en
agosto de 2026; se trata como intervenida). Solo incluye EPS con afiliados entre diciembre de 2024 y
septiembre de 2026.

## 11. Vacíos conocidos

- Regímenes de excepción y especiales: en SISPRO aparecen incompletos antes de 2018 (unas 388.000
  personas en diciembre de 2013 frente a unos 2 millones desde 2018). La relación afiliados/población
  total no es comparable antes y después de ese año; con solo contributivo y subsidiado se mantuvo
  cerca de 94 %. No se intenta corregir la serie: casi no hay información adicional sobre esos regímenes.

- El extracto de SISPRO no tiene los meses de enero a octubre de 2010, enero de 2011 ni enero
  a marzo de 2012.
- No hay EPS × municipio × grupo etario con historia. Para reconstruirlo hace falta el acceso a
  los cubos BDUA de SISPRO o una solicitud de información a la ADRES o a MinSalud.
- El tablero histórico de MinSalud en Tableau Public (diciembre de 2018 a junio de 2025)
  rechazó las consultas automatizadas. Puede intentarse manualmente desde el navegador.
- La ADRES publica en `datos.gov.co` muchas "vistas" filtradas por municipio. No son fuentes
  distintas: son subconjuntos de los dos conjuntos nacionales que se usan aquí.

## 12. Uso de inteligencia artificial

La búsqueda de fuentes, la descarga, el OCR, la transcripción de parámetros y los scripts los
hizo Claude (Anthropic) a pedido de David Aguilar y Camila Gómez, que definieron el alcance y aportaron las bases territoriales. Los totales se validaron cruzando fuentes
independientes (sección 2) y los parámetros de la UPC contra las tablas por edad de cada
resolución (sección 3). Antes de usar cifras para decisiones, revise los valores directamente
en la norma citada.
