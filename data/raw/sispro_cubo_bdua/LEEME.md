# Extracto del cubo BDUA (SISPRO)

Fuente: "Construya su consulta – Aseguramiento", Central de Gestión del Conocimiento, SISPRO
https://www.sispro.gov.co/central-gestion-del-conocimiento/Pages/construya-su-consulta-aseguramiento.aspx

El tablero es un informe público de Power BI ("publicar en la web"). Los datos se obtuvieron el
15 de octubre de 2026 con las mismas consultas que hace el visor (ver `sispro()` en
`scripts/00_descargar_fuentes.py`): una por mes, agrupando por código de municipio, régimen y
estado de afiliación.

- `municipio_regimen_estado_mensual.csv.gz`: periodo (AAAAMM), cod_municipio, régimen, estado, afiliados.
  187 meses entre dic. 2009 y ago. 2026. Incluye registros no vigentes (retirados, fallecidos):
  ver docs/metodologia.md.
- `geografia.csv`: dimensión geográfica del modelo (código DANE, nombre, categoría de ruralidad,
  área de gestión).
