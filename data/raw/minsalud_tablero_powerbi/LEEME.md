# Tablero Power BI "Cifras de afiliación en salud" (MinSalud)

Tablas extraídas el 15 de octubre de 2026 del informe público enlazado en
https://minsalud.gov.co/Proteccion-Social/Paginas/cifras-aseguramiento-salud.aspx
(tabla `ConsolidadoEPS` y dimensión `EPS` del modelo).

- `eps_municipio_regimen_cod_eps.csv`: afiliados por código de EPS, municipio y régimen.
  Cortes: dic. 2024, dic. 2025, jul. 2026, ago. 2026 y sep. 2026 (`fecha_corte` = primer día del mes).
- `catalogo_eps.csv`: código de habilitación → nombre corto → régimen. Sirve para unir los
  libros mensuales (que usan nombre corto) con la BDUA de la ADRES (que usa código).
