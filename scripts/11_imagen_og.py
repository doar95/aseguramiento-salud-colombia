"""Miniatura para redes (og:image 1200x630): mapa municipal de zonas UPC 2026 y cifras clave."""
from pathlib import Path
import json
import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

RAIZ = Path(__file__).resolve().parents[1]
D = RAIZ / "docs" / "data"
g = gpd.read_file(D / "municipios.geojson")
af = json.loads((D / "afiliacion_municipio.json").read_text(encoding="utf-8"))
nac = json.loads((D / "afiliacion_nacional.json").read_text(encoding="utf-8"))
k = len(af["periodos"]) - 1
def pct_s(c):
    v = af["datos"].get(c, [[None] * 4])[k]
    return None if not v or not v[3] else v[1] / v[3]
g["s"] = g["cod"].map(pct_s)
AZ, AZO, AM = "#3366CC", "#004884", "#FFAB00"
fig = plt.figure(figsize=(12, 6.3), dpi=100)
fig.patch.set_facecolor("#FFFFFF")
ax = fig.add_axes([0.56, 0.02, 0.43, 0.96])
g.plot(column="s", cmap="YlGnBu", vmin=0.2, vmax=1, ax=ax, linewidth=0.05, edgecolor="#ffffff",
       missing_kwds={"color": "#dddddd"})
ax.set_axis_off()
fig.text(0.04, 0.86, "Aseguramiento en salud", fontsize=34, fontweight="bold", color=AZO, family="DejaVu Serif")
fig.text(0.04, 0.78, "en Colombia, 2013–2026", fontsize=34, fontweight="bold", color=AZO, family="DejaVu Serif")
fig.text(0.04, 0.70, "Afiliación por municipio · EPS · UPC y zonas · Finanzas ADRES",
         fontsize=13, color="#4B4B4B")
t = nac["total"][-1]; p = nac["periodo"][-1]
fig.text(0.04, 0.52, f"{t/1e6:,.1f} millones".replace(".", ","), fontsize=40, fontweight="bold", color=AZ)
fig.text(0.04, 0.46, f"afiliados vigentes ({p[4:]}/{p[:4]}, SISPRO)", fontsize=14, color="#4B4B4B")
fig.text(0.04, 0.33, "Mapa: participación del régimen subsidiado por municipio", fontsize=12, color="#4B4B4B")
fig.text(0.04, 0.10, "Datos abiertos de MinSalud, ADRES, SISPRO, DANE y Supersalud", fontsize=12, color="#4B4B4B")
fig.text(0.04, 0.05, "Claude (Anthropic), David Aguilar y Camila Gómez", fontsize=12, color=AZO, fontweight="bold")
fig.add_artist(plt.Rectangle((0, 0.975), 1, 0.025, transform=fig.transFigure, color=AZO))
fig.add_artist(plt.Rectangle((0.04, 0.62), 0.12, 0.008, transform=fig.transFigure, color=AM))
fig.savefig(RAIZ / "docs" / "assets" / "og.png", dpi=100)
print("ok")
