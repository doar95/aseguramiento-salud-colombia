/* Utilidades compartidas por las páginas del sitio (menú, idioma, formato, estado en la URL). */
"use strict";
const REPO = "https://github.com/doar95/aseguramiento-salud-colombia/blob/main/";
const PAGINAS = [["index.html", "Inicio", "Home"], ["mapa.html", "Mapa", "Map"], ["afiliacion.html", "Afiliación", "Enrollment"],
  ["eps.html", "EPS", "Insurers (EPS)"], ["finanzas.html", "Finanzas", "Finances"], ["corte.html", "Corte Constitucional", "Constitutional Court"]];
let LANG = "es";
try { if (localStorage.getItem("lang") === "en") LANG = "en"; } catch (e) {}
const TXT = {};          // TXT.en[clave] lo define cada página
const tt = (k, es) => (LANG === "en" && TXT.en && TXT.en[k]) ? TXT.en[k] : (es ?? k);

function cabecera(activa) {
  const g = document.createElement("div");
  g.className = "govbar";
  g.innerHTML = `<b>${LANG === "es" ? "Repositorio abierto · datos públicos del Estado colombiano" : "Open repository · Colombian public data"}</b>
    <span><button id="b-es" type="button" class="${LANG === "es" ? "on" : ""}">ES</button> <button id="b-en" type="button" class="${LANG === "en" ? "on" : ""}">EN</button></span>`;
  const m = document.createElement("nav");
  m.className = "menu";
  m.setAttribute("aria-label", "Secciones");
  m.innerHTML = PAGINAS.map(([h, es, en]) => `<a href="${h}" class="${h === activa ? "on" : ""}">${LANG === "es" ? es : en}</a>`).join("") +
    `<a href="https://github.com/doar95/aseguramiento-salud-colombia">GitHub ↗</a>`;
  document.body.prepend(m);
  document.body.prepend(g);
  g.querySelector("#b-es").onclick = () => cambiarIdioma("es");
  g.querySelector("#b-en").onclick = () => cambiarIdioma("en");
}
function cambiarIdioma(l) { try { localStorage.setItem("lang", l); } catch (e) {} location.reload(); }
function traducir() {
  document.documentElement.lang = LANG;
  if (LANG === "es") return;
  document.querySelectorAll("[data-i18n]").forEach(e => { const v = TXT.en && TXT.en[e.dataset.i18n]; if (v) e.innerHTML = v; });
}
const LOC = () => LANG === "es" ? "es-CO" : "en-US";
const fmt = (v, d = 0) => v == null || !isFinite(v) ? "–" : Number(v).toLocaleString(LOC(), { maximumFractionDigits: d, minimumFractionDigits: d });
const pct = (v, d = 1) => v == null || !isFinite(v) ? "–" : fmt(v * 100, d) + " %";
const mill = (v, d = 2) => v == null || !isFinite(v) ? "–" : fmt(v / 1e6, d) + " M";
const bill = (v, d = 2) => v == null || !isFinite(v) ? "–" : fmt(v / 1e12, d) + (LANG === "es" ? " billones" : " tn");

const _cache = {};
function cargar(nombre) { return _cache[nombre] || (_cache[nombre] = fetch("data/" + nombre).then(r => r.json())); }

/* Estado en la URL: ?a=1&b=2  */
function leerURL() { return Object.fromEntries(new URLSearchParams(location.search)); }
function escribirURL(obj) {
  const p = new URLSearchParams();
  Object.entries(obj).forEach(([k, v]) => { if (v !== "" && v != null && v !== false) p.set(k, v); });
  history.replaceState(null, "", location.pathname + (p.toString() ? "?" + p : ""));
}
function compartir() {
  const u = location.href;
  const ok = () => aviso(LANG === "es" ? "Enlace copiado: muestra esta misma vista" : "Link copied: it opens this same view");
  if (navigator.share && /Mobi/.test(navigator.userAgent)) { navigator.share({ url: u, title: document.title }).catch(() => {}); return; }
  if (navigator.clipboard) navigator.clipboard.writeText(u).then(ok, () => prompt("URL", u)); else prompt("URL", u);
}
function aviso(t) { const d = document.createElement("div"); d.className = "toast"; d.textContent = t; document.body.append(d); setTimeout(() => d.remove(), 2600); }

/* Gráficas (Chart.js) */
const charts = {};
function colTexto() { return getComputedStyle(document.body).getPropertyValue("--texto").trim() || "#1F1F1F"; }
function opcBase(titulo, apilado, extra = {}) {
  const c = colTexto();
  return Object.assign({
    responsive: true, maintainAspectRatio: false, animation: false, interaction: { mode: "index", intersect: false },
    plugins: { title: { display: !!titulo, text: titulo, color: c, font: { family: "Work Sans", size: 13, weight: "600" } },
      legend: { labels: { color: c, boxWidth: 12, font: { size: 11 } } },
      tooltip: { callbacks: { label: x => `${x.dataset.label}: ${fmt(x.parsed.y ?? x.parsed.x, 2)}` } } },
    scales: { x: { stacked: !!apilado, ticks: { color: c, maxTicksLimit: 14, font: { size: 10 } }, grid: { display: false } },
      y: { stacked: !!apilado, ticks: { color: c, font: { size: 10 } }, grid: { color: "#8882" } } }
  }, extra);
}
function grafica(id, cfg) { if (charts[id]) charts[id].destroy(); charts[id] = new Chart(document.getElementById(id), cfg); return charts[id]; }
const PAL = ["#004884", "#3366CC", "#6F99E3", "#069169", "#7BC8A4", "#FFAB00", "#F6C86B", "#8C6BB1", "#B2DF8A", "#4B4B4B", "#9E9E9E", "#9B59B6", "#C39BD3", "#2C3E50", "#BDBDBD", "#7F8C8D"];
const RAMP = ["#FFFFCC", "#A1DAB4", "#41B6C4", "#2C7FB8", "#253494"];
const DIV = ["#8C510A", "#D8B365", "#F5F5F5", "#5AB4AC", "#01665E"];
function quantiles(vals, k = 5) {
  const v = vals.filter(x => x != null && isFinite(x)).sort((a, b) => a - b);
  if (!v.length) return [0, 0, 0, 0];
  return Array.from({ length: k - 1 }, (_, i) => v[Math.floor((i + 1) / k * (v.length - 1))]);
}
function claseColor(v, br, pal = RAMP) { if (v == null || !isFinite(v)) return null; let i = 0; while (i < br.length && v > br[i]) i++; return pal[i]; }
function opciones(sel, pares, conTodos) {
  sel.innerHTML = (conTodos ? `<option value="">${conTodos}</option>` : "") + pares.map(([v, l]) => `<option value="${v}">${l}</option>`).join("");
}
function piePagina() {
  const f = document.createElement("footer");
  f.className = "pie";
  f.innerHTML = (LANG === "es"
    ? "Claude (Anthropic), David Aguilar y Camila Gómez. Datos abiertos de MinSalud, ADRES, SISPRO, DANE, Supersalud y Corte Constitucional. Código: licencia MIT; datos derivados de la ADRES: CC BY-SA 4.0. No es una publicación oficial de ninguna entidad."
    : "Claude (Anthropic), David Aguilar and Camila Gómez. Open data from MinSalud, ADRES, SISPRO, DANE, Supersalud and the Constitutional Court. Code: MIT; ADRES-derived data: CC BY-SA 4.0. Not an official publication of any agency.") +
    ` · <a href="https://github.com/doar95/aseguramiento-salud-colombia">GitHub</a>`;
  document.body.append(f);
}

/* Tabla con búsqueda y orden por columna. cols: [{t, num, fm, cls}], filas: arrays (valores crudos), extra: {onRow(fila), marca(fila)} */
function tablaOrdenable(cont, cols, filas, extra = {}) {
  const st = cont._st || (cont._st = {q: "", k: extra.k ?? 1, dir: -1});
  cont.innerHTML = `<input type="search" class="buscar" placeholder="${LANG === "es" ? "Buscar…" : "Search…"}" value="${st.q.replace(/"/g, "&quot;")}" style="font:inherit;padding:4px 8px;border:1px solid var(--borde);border-radius:4px;margin:0 0 6px;width:min(320px,100%);background:var(--fondo);color:var(--texto)">
    <div class="scroll"><table class="tbl"><thead><tr>${cols.map((c, i) => `<th class="${c.num ? "" : "l"}" data-i="${i}" style="cursor:pointer">${c.t}${st.k === i ? (st.dir < 0 ? " ▼" : " ▲") : ""}</th>`).join("")}</tr></thead><tbody></tbody></table></div>
    <p class="nota" style="margin:2px 0"></p>`;
  const norm = x => String(x).normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
  const pinta = () => {
    const q = norm(st.q), f = filas.filter(r => !q || norm(r[0]).includes(q) || (extra.buscarEn && norm(r[extra.buscarEn]).includes(q)));
    f.sort((a, b) => { const x = a[st.k], y = b[st.k]; if (x == null) return 1; if (y == null) return -1; return (typeof x === "number" ? x - y : String(x).localeCompare(String(y))) * st.dir; });
    const tb = cont.querySelector("tbody"), lim = 400;
    tb.innerHTML = f.slice(0, lim).map((r, i) => `<tr data-r="${filas.indexOf(r)}" style="${extra.onRow ? "cursor:pointer;" : ""}${extra.marca && extra.marca(r) ? "background:var(--azul-cl)" : ""}">${cols.map((c, j) => `<td class="${c.num ? "" : "l"}">${c.fm ? c.fm(r[j], r) : (r[j] ?? "–")}</td>`).join("")}</tr>`).join("");
    cont.querySelector("p.nota").textContent = f.length > lim ? (LANG === "es" ? `Se muestran ${lim} de ${f.length} filas; use la búsqueda.` : `Showing ${lim} of ${f.length} rows; use search.`) : `${f.length} ${LANG === "es" ? "filas" : "rows"}`;
    if (extra.onRow) tb.querySelectorAll("tr").forEach(tr => tr.onclick = () => extra.onRow(filas[+tr.dataset.r]));
  };
  cont.querySelector("input").oninput = e => { st.q = e.target.value; pinta(); };
  cont.querySelectorAll("th").forEach(th => th.onclick = () => { const i = +th.dataset.i; st.dir = st.k === i ? -st.dir : (cols[i].num ? -1 : 1); st.k = i; tablaOrdenable(cont, cols, filas, extra); });
  pinta();
}
