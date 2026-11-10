// Primera Lectura — sitio estático. Lee site/data/*.json (los genera scripts/exportar_web.py).
"use strict";

const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const sinTildes = (s) => String(s ?? "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();

const SEMAFORO = { rojo: "Alerta roja", amarillo: "Atención", verde: "Sin riesgo relevante", sin: "Sin leer" };
const AVANCE = ["Archivado o retirado", "Presentado", "En comisión", "Con dictamen", "En el Pleno", "Aprobado"];
const ICONO = {
  check: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" aria-hidden="true"><path d="M5 12.5l4.5 4.5L19 7.5"/></svg>',
  alerta: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" aria-hidden="true"><path d="M12 4l9 16H3z"/><path d="M12 10v4M12 17.5v.5"/></svg>',
  pdf: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M7 3h7l5 5v13H7z"/><path d="M14 3v5h5M9.5 13h5M9.5 16.5h5"/></svg>',
  externo: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M14 4h6v6M20 4l-9 9M18 14v6H4V6h6"/></svg>',
  cerrar: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18"/></svg>',
};

const estado = { q: "", semaforo: new Set(), avance: new Set(), camara: new Set(), tema: "", bancada: "", visibles: 40 };
let P = [], V = [], META = {};

const sem = (p) => (p.lectura ? p.lectura.semaforo : "sin");
const fecha = (iso) => (iso ? iso.split("-").reverse().join("/") : "");
const codigo = (p) => p.pl.replace(/^0+/, "").replace("-2026-2031", "");
// El portal entrega títulos y sumillas EN MAYÚSCULAS: se pasan a tipo oración para poder leerlos.
const SIGLAS_OK = /\b(PCM|MEF|ONG|SUNAT|INEI|PNP|JNJ|JNE|ONPE|RENIEC|ESSALUD|SUNEDU|MINSA|OIT|ONU|CIDH|COVID|REINFO|TUO|DS|DL|PL|PRL|CD)\b/gi;
const oracion = (s) => {
  if (!s || s !== s.toUpperCase()) return s || "";
  const t = s.toLowerCase().replace(SIGLAS_OK, (m) => m.toUpperCase());
  return t.charAt(0).toUpperCase() + t.slice(1);
};

// ---------------- carga ----------------
async function iniciar() {
  try {
    [P, V, META] = await Promise.all(["proyectos", "votaciones", "meta"].map((n) => fetch(`data/${n}.json`).then((r) => {
      if (!r.ok) throw new Error(n);
      return r.json();
    })));
  } catch (e) {
    $("#cargando").textContent = "No se pudieron cargar los datos. Si abriste el archivo directamente, sírvelo con «python -m http.server» desde la carpeta site/.";
    return;
  }
  $("#cargando").hidden = true;
  $("#actualizado").textContent = `Datos al ${fecha(META.actualizado)}.`;
  prepararFiltros();
  portada();
  window.addEventListener("hashchange", ruta);
  ruta();
}

// ---------------- rutas ----------------
function ruta() {
  const h = location.hash.replace(/^#\/?/, "");
  const [seccion, id] = h.split("/");
  const vista = ["votaciones", "panorama", "como-funciona"].includes(seccion) ? seccion : "proyectos";
  const antes = $$(".vista").find((v) => !v.hidden)?.id;
  $$(".vista").forEach((v) => (v.hidden = v.id !== `vista-${vista}`));
  if (antes && antes !== `vista-${vista}`) window.scrollTo(0, 0);
  $$(".barra nav a").forEach((a) => (a.dataset.ruta === vista ? a.setAttribute("aria-current", "page") : a.removeAttribute("aria-current")));
  if (vista === "proyectos") pintarLista();
  if (vista === "votaciones") pintarVotaciones();
  if (vista === "panorama") pintarPanorama();
  if (seccion === "p" && id) abrirFicha(decodeURIComponent(id));
  else if ($("#ficha").open) $("#ficha").close();
}

// ---------------- portada: el titular sale de los datos ----------------
function portada() {
  const ultima = new Date(META.actualizado + "T00:00:00");
  const hace7 = new Date(ultima); hace7.setDate(ultima.getDate() - 7);
  const semana = P.filter((p) => new Date(p.fecha + "T00:00:00") > hace7);
  const rojosSemana = semana.filter((p) => sem(p) === "rojo").length;
  const vigentesRojos = P.filter((p) => sem(p) === "rojo" && p.avance > 0);
  $("#titular").innerHTML = `En los últimos siete días se presentaron <span class="cifra">${semana.length}</span> proyectos de ley. ` +
    (rojosSemana ? `<span class="marcado"><span class="cifra">${rojosSemana}</span> ${rojosSemana === 1 ? "podría" : "podrían"} afectar derechos.</span>` :
      `<span class="marcado"><span class="cifra">${vigentesRojos.length}</span> proyectos vigentes podrían afectar derechos.</span>`);
  $("#bajada").textContent = `Primera Lectura revisa todos los días los ${P.length} proyectos del periodo 2026-2031 en Diputados y Senado. ` +
    `La IA ya leyó el articulado de ${META.n_lecturas}; cada alerta trae la cita del artículo que la sustenta.`;

  // primero las alertas con más sustento: revisadas por el agente y con la cita verificada en el PDF
  const sustento = (p) => (p.lectura.por === "agente" ? 2 : 0) + (p.lectura.cita_ok ? 1 : 0);
  const orden = vigentesRojos.sort((a, b) => sustento(b) - sustento(a) || b.avance - a.avance || b.fecha.localeCompare(a.fecha)).slice(0, 6);
  $("#lista-alertas").innerHTML = orden.map((p) => `
    <li class="alerta">
      <div class="alerta-meta">
        <span class="semaforo rojo"><i class="punto rojo"></i>${SEMAFORO.rojo}</span>
        <strong>PL ${esc(codigo(p))}</strong>
        <span>${esc(AVANCE[p.avance])}</span>
        <span>${esc(p.bancada)}</span>
      </div>
      <div>
        <h3><button type="button" data-abrir="${esc(p.id)}">${esc(p.lectura.resumen || oracion(p.titulo))}</button></h3>
        ${citaHTML(p.lectura)}
      </div>
    </li>`).join("");
}

function citaHTML(l) {
  if (!l || !l.cita) return "";
  const ok = l.cita_ok
    ? `<span class="verificada">${ICONO.check}Cita verificada en el PDF</span>`
    : `<span class="verificada no">${ICONO.alerta}No se encontró esta cita en el PDF</span>`;
  return `<blockquote class="cita ${esc(l.semaforo)}"><mark>${esc(l.cita)}</mark></blockquote>${ok}`;
}

// ---------------- filtros y lista ----------------
function prepararFiltros() {
  const temas = [...new Set(P.map((p) => p.tema).filter(Boolean))].sort();
  const bancadas = [...new Set(P.map((p) => p.bancada))].sort();
  $('select[name="tema"]').insertAdjacentHTML("beforeend", temas.map((t) => `<option>${esc(t)}</option>`).join(""));
  $('select[name="bancada"]').insertAdjacentHTML("beforeend", bancadas.map((t) => `<option>${esc(t)}</option>`).join(""));
  $$(".fichas button").forEach((b) => b.setAttribute("aria-pressed", "false"));

  const f = $("#filtros");
  f.addEventListener("input", (e) => {
    if (e.target.name === "q") estado.q = sinTildes(e.target.value);
    if (e.target.name === "tema") estado.tema = e.target.value;
    if (e.target.name === "bancada") estado.bancada = e.target.value;
    estado.visibles = 40;
    pintarLista();
  });
  f.addEventListener("click", (e) => {
    const b = e.target.closest(".fichas button");
    if (!b) return;
    const grupo = estado[b.parentElement.dataset.filtro];
    const v = b.dataset.valor;
    grupo.has(v) ? grupo.delete(v) : grupo.add(v);
    b.setAttribute("aria-pressed", String(grupo.has(v)));
    estado.visibles = 40;
    pintarLista();
  });
  f.addEventListener("reset", () => {
    Object.assign(estado, { q: "", tema: "", bancada: "", visibles: 40 });
    ["semaforo", "avance", "camara"].forEach((k) => estado[k].clear());
    $$(".fichas button").forEach((b) => b.setAttribute("aria-pressed", "false"));
    setTimeout(pintarLista);
  });
  $("#mas").addEventListener("click", () => { estado.visibles += 60; pintarLista(); });
  $("#descargar").addEventListener("click", descargarCSV);
  document.addEventListener("click", (e) => {
    const b = e.target.closest("[data-abrir]");
    if (b) location.hash = `#/p/${encodeURIComponent(b.dataset.abrir)}`;
  });
}

function filtrados() {
  const O = { rojo: 0, amarillo: 1, verde: 2, sin: 3 };
  return P.filter((p) =>
    (!estado.q || sinTildes(`${p.titulo} ${p.sumilla} ${p.pl} ${p.autor}`).includes(estado.q)) &&
    (!estado.semaforo.size || estado.semaforo.has(sem(p))) &&
    (!estado.avance.size || estado.avance.has(String(p.avance))) &&
    (!estado.camara.size || estado.camara.has(p.camara)) &&
    (!estado.tema || p.tema === estado.tema) &&
    (!estado.bancada || p.bancada === estado.bancada)
  ).sort((a, b) => O[sem(a)] - O[sem(b)] || b.fecha.localeCompare(a.fecha));
}

function avanceHTML(n) {
  const tramos = [1, 2, 3, 4, 5].map((i) => `<i class="${n >= i ? "on" : ""}"></i>`).join("");
  return `<span class="avance ${n === 0 ? "archivado" : ""}" aria-hidden="true">${tramos}</span><span class="avance-texto">${AVANCE[n]}</span>`;
}

function pintarLista() {
  const r = filtrados();
  $("#conteo").textContent = `${r.length} de ${P.length} proyectos`;
  $("#lista").innerHTML = r.length ? r.slice(0, estado.visibles).map((p) => `
    <li class="fila">
      <button type="button" data-abrir="${esc(p.id)}">
        <span class="fila-cod"><b>PL ${esc(codigo(p))}</b><span>${fecha(p.fecha)}</span><span>${p.camara === "senado" ? "Senado" : "Diputados"}</span></span>
        <span>
          <span class="fila-titulo">${esc(p.lectura?.resumen || oracion(p.titulo))}</span>
          <span class="fila-datos"><span>${esc(p.tema)}</span><span>${esc(p.bancada)}</span></span>
        </span>
        <span class="fila-der">
          <span class="semaforo ${sem(p)}"><i class="punto ${sem(p)}"></i>${SEMAFORO[sem(p)]}</span>
          ${avanceHTML(p.avance)}
        </span>
      </button>
    </li>`).join("") : `<li class="fila" style="padding:1.5rem 1rem">Ningún proyecto cumple estos filtros. Prueba quitando alguno o usa «Limpiar filtros».</li>`;
  $("#mas").hidden = r.length <= estado.visibles;
}

function descargarCSV() {
  const cols = ["camara", "pl", "fecha", "titulo", "tema", "bancada", "autor", "estado"];
  const filas = filtrados().map((p) => [...cols.map((c) => p[c]), sem(p), p.lectura?.resumen || "", p.lectura?.cita || "", p.pdf]);
  const csv = [[...cols, "semaforo", "resumen_ia", "cita", "pdf"], ...filas]
    .map((f) => f.map((v) => `"${String(v ?? "").replace(/"/g, '""')}"`).join(",")).join("\n");
  const a = Object.assign(document.createElement("a"), {
    href: URL.createObjectURL(new Blob(["﻿" + csv], { type: "text/csv" })), download: "primera_lectura.csv",
  });
  a.click();
  URL.revokeObjectURL(a.href);
}

// ---------------- ficha ----------------
function abrirFicha(id) {
  const p = P.find((x) => x.id === id);
  if (!p) return;
  const l = p.lectura;
  const lectura = l ? `
    <section class="lectura ${esc(l.semaforo)}" aria-label="Primera lectura de la IA">
      <div class="lectura-cabeza">
        <span class="semaforo ${esc(l.semaforo)}"><i class="punto ${esc(l.semaforo)}"></i>${SEMAFORO[l.semaforo]}</span>
        <span class="lectura-por">${l.por === "agente" ? "Segunda lectura: revisada por el agente" : "Primera lectura: modelo local qwen2.5"}</span>
      </div>
      <p class="resumen">${esc(l.resumen)}</p>
      ${citaHTML(l)}
      <p>${esc(l.explicacion)}</p>
      ${l.derechos.length ? `<div class="etiquetas">${l.derechos.map((d) => `<span>${esc(d)}</span>`).join("")}</div>` : ""}
      ${l.estandares.length ? `<ul class="estandares">${l.estandares.map((s) => `<li>${esc(s)}</li>`).join("")}</ul>` : ""}
      ${l.revisar ? `<p class="aviso-revisar">El sustento de esta lectura está incompleto; está en cola para la segunda lectura.</p>` : ""}
    </section>` : `<p class="sin-lectura">La IA todavía no leyó este proyecto: no pasó el filtro de temas sensibles o está en cola.</p>`;

  const votos = V.filter((v) => v.camara === p.camara && v.pls.includes(p.pl));
  const datos = [["Temática", p.tema + (p.temas2 ? ` (también: ${p.temas2})` : "")], ["Bancada", p.bancada], ["Autor", p.autor],
    ["Coautores", p.coautores.replaceAll("; ", ", ")], ["Comisión", p.comision], ["Estado", p.estado]].filter(([, v]) => v);

  $("#ficha-contenido").innerHTML = `
    <div class="ficha-cabeza">
      <div><p>PL ${esc(codigo(p))} · ${p.camara === "senado" ? "Senado" : "Cámara de Diputados"} · presentado el ${fecha(p.fecha)}</p></div>
      <button class="cerrar" type="button" aria-label="Cerrar la ficha" id="cerrar">${ICONO.cerrar}</button>
    </div>
    <h2 class="titulo-ley" id="ficha-titulo">${esc(oracion(p.titulo))}</h2>
    ${lectura}
    <section><h3>Sumilla</h3><p>${esc(oracion(p.sumilla))}</p></section>
    <dl class="datos">${datos.map(([k, v]) => `<dt>${k}</dt><dd>${esc(v)}</dd>`).join("")}</dl>
    <div class="enlaces">
      <a href="${esc(p.pdf)}" target="_blank" rel="noopener">${ICONO.pdf}PDF del proyecto</a>
      <a href="${esc(p.url)}" target="_blank" rel="noopener">${ICONO.externo}Expediente en el portal del Congreso</a>
    </div>
    ${votos.length ? `<section><h3>Votaciones en el Pleno</h3>${votos.map(votoHTML).join("")}</section>` : ""}
    <section><h3>Recorrido</h3><ol class="recorrido">${p.recorrido.map(([f, e, d]) =>
      `<li><time>${fecha(f)}</time><b>${esc(e)}</b>${d ? `<br>${esc(d)}` : ""}</li>`).join("")}</ol></section>`;

  const dlg = $("#ficha");
  if (!dlg.open) dlg.showModal();
  $("#cerrar").addEventListener("click", () => dlg.close());
}

$("#ficha").addEventListener("close", () => {
  if (location.hash.startsWith("#/p/")) history.replaceState(null, "", "#/");
});
$("#ficha").addEventListener("click", (e) => { if (e.target.id === "ficha") e.target.close(); });

// ---------------- votaciones ----------------
const NOMBRE = (s) => META.bancadas?.[s] || s;

function votoHTML(v) {
  const aprob = v.resultado === "Aprobado";
  const filas = v.bancadas ? Object.entries(v.bancadas).map(([b, n]) => {
    const total = n.reduce((a, x) => a + x, 0) || 1;
    const seg = ["si", "no", "abst", "sr"].map((c, i) => n[i] ? `<span class="c-${c}" style="width:${(n[i] / total) * 100}%" title="${n[i]}"></span>` : "").join("");
    return `<span>${esc(NOMBRE(b))}</span><span class="barra-v" role="img" aria-label="${esc(NOMBRE(b))}: ${n[0]} sí, ${n[1]} no, ${n[2]} abstenciones">${seg}</span><span>${n[0]}/${total}</span>`;
  }).join("") : "";
  return `<div class="voto">
    <div class="voto-cabeza"><span class="resultado ${aprob ? "si" : "no"}">${esc(v.resultado || "Sin resultado")}</span><span class="totales">${fecha(v.fecha)}</span></div>
    <p>${esc(oracion(v.movimiento))}</p>
    <p class="totales">A favor ${esc(v.si || "—")}, en contra ${esc(v.no || "—")}, abstenciones ${esc(v.abst || "—")}</p>
    ${filas ? `<div class="apilada">${filas}</div><div class="leyenda"><span><i class="c-si"></i>Sí</span><span><i class="c-no"></i>No</span><span><i class="c-abst"></i>Abstención</span><span><i class="c-sr"></i>Sin respuesta</span></div>` :
      `<p class="totales">Acta sin votación nominal: solo el resultado.</p>`}
  </div>`;
}
const cap = (s) => (s ? s.charAt(0) + s.slice(1).toLowerCase() : "");

let camaraVot = "diputados";
$$(".selector-camara button").forEach((b) => b.addEventListener("click", () => {
  camaraVot = b.dataset.camara;
  $$(".selector-camara button").forEach((x) => x.setAttribute("aria-selected", String(x === b)));
  pintarVotaciones();
}));

function pintarVotaciones() {
  const vs = V.filter((v) => v.camara === camaraVot && v.tipo === "Votación" && v.votos.length);
  // posición mayoritaria y cohesión de cada bancada en cada votación
  const pos = {}, coh = {};
  vs.forEach((v) => {
    const g = {};
    v.votos.filter(([, , c]) => ["SI", "NO", "Abst."].includes(c)).forEach(([, b, c]) => ((g[b] ||= {})[c] = (g[b][c] || 0) + 1));
    Object.entries(g).forEach(([b, cuenta]) => {
      const [top, n] = Object.entries(cuenta).sort((a, x) => x[1] - a[1])[0];
      const tot = Object.values(cuenta).reduce((a, x) => a + x, 0);
      (pos[b] ||= {})[v.id] = top;
      (coh[b] ||= []).push(n / tot);
    });
  });
  const bancadas = Object.keys(coh).sort((a, b) => avg(coh[b]) - avg(coh[a]));
  $("#cohesion").innerHTML = bancadas.map((b) => `<div class="barra-h"><span>${esc(NOMBRE(b))}</span>
    <span class="pista"><span style="width:${avg(coh[b]) * 100}%"></span></span><b>${Math.round(avg(coh[b]) * 100)}%</b></div>`).join("");

  const n = bancadas.length;
  let m = `<div></div>` + bancadas.map((b) => `<div class="rot" title="${esc(NOMBRE(b))}">${esc(b)}</div>`).join("");
  bancadas.forEach((a) => {
    m += `<div class="rot" title="${esc(NOMBRE(a))}">${esc(b2(a))}</div>`;
    bancadas.forEach((b) => {
      const ids = Object.keys(pos[a] || {}).filter((id) => pos[b]?.[id]);
      const pct = ids.length ? ids.filter((id) => pos[a][id] === pos[b][id]).length / ids.length : 0;
      const fondo = `rgba(74,60,140,${0.08 + pct * 0.85})`;
      m += `<div style="background:${fondo};color:${pct > 0.55 ? "#fff" : "var(--tinta)"}" title="${esc(NOMBRE(a))} y ${esc(NOMBRE(b))}: ${Math.round(pct * 100)}%">${Math.round(pct * 100)}%</div>`;
    });
  });
  const mz = $("#coincidencia");
  mz.style.gridTemplateColumns = `5.5rem repeat(${n}, 1fr)`;
  mz.innerHTML = m;

  $("#lista-votaciones").innerHTML = vs.sort((a, b) => b.fecha.localeCompare(a.fecha)).map((v) => `
    <details>
      <summary><span class="totales">${fecha(v.fecha)}</span><span class="asunto">PL ${esc(v.pls.map((x) => x.replace(/^0+/, "").replace("-2026-2031", "")).join(", "))}: ${esc(oracion(v.movimiento))}</span>
        <span class="resultado ${v.resultado === "Aprobado" ? "si" : "no"}">${esc(v.resultado)}</span></summary>
      <div class="cuerpo">
        <p>${esc(oracion(v.asunto))}</p>
        ${votoHTML(v)}
        <p class="totales">Lectura del PDF: ${esc(v.fuente)}. Control contra los totales impresos: ${esc(v.control)}. <a href="${esc(v.url)}" target="_blank" rel="noopener">Ver el PDF de la votación</a></p>
      </div>
    </details>`).join("");

  const nombres = [...new Set(vs.flatMap((v) => v.votos.map(([c]) => c)))].sort();
  $("#congresistas").innerHTML = nombres.map((c) => `<option value="${esc(c)}">`).join("");
  const inp = $("#buscar-congresista");
  inp.oninput = () => {
    const c = nombres.find((x) => x === inp.value);
    if (!c) { $("#historial").innerHTML = ""; return; }
    const TXT = { SI: "Sí", NO: "No", "Abst.": "Abstención", SinRes: "Sin respuesta", AUS: "Ausente", "***": "Presidía (no vota)" };
    const filas = vs.map((v) => [v, v.votos.find(([x]) => x === c)]).filter(([, x]) => x);
    $("#historial").innerHTML = `<table><thead><tr><th>Fecha</th><th>Proyecto y votación</th><th>Voto</th></tr></thead><tbody>${filas.map(([v, x]) =>
      `<tr><td>${fecha(v.fecha)}</td><td>PL ${esc(v.pls.join(", "))}: ${esc(oracion(v.movimiento))}</td><td><b>${esc(TXT[x[2]] || x[2])}</b></td></tr>`).join("")}</tbody></table>`;
  };
}
const avg = (a) => a.reduce((x, y) => x + y, 0) / a.length;
const b2 = (s) => s;

// ---------------- panorama ----------------
function pintarPanorama() {
  const temas = [...new Set(P.map((p) => p.tema).filter(Boolean))].sort();
  const bancadas = [...new Set(P.map((p) => p.bancada))].sort();
  const cuenta = {};
  P.forEach((p) => { const k = `${p.tema}|${p.bancada}`; cuenta[k] = (cuenta[k] || 0) + 1; });
  const max = Math.max(...Object.values(cuenta));
  $("#mapa-calor").innerHTML = `<table><thead><tr><th></th>${bancadas.map((b) => `<th scope="col">${esc(b)}</th>`).join("")}</tr></thead><tbody>${
    temas.map((t) => `<tr><th scope="row">${esc(t)}</th>${bancadas.map((b) => {
      const n = cuenta[`${t}|${b}`] || 0;
      const a = n ? 0.08 + (n / max) * 0.9 : 0.03;
      return `<td><button type="button" data-tema="${esc(t)}" data-bancada="${esc(b)}" style="background:rgba(74,60,140,${a});color:${n / max > 0.5 ? "#fff" : "var(--tinta)"}" aria-label="${n} proyectos de ${esc(t)} de ${esc(b)}">${n || ""}</button></td>`;
    }).join("")}</tr>`).join("")}</tbody></table>`;
  $$("#mapa-calor button").forEach((b) => b.addEventListener("click", () => {
    estado.tema = b.dataset.tema; estado.bancada = b.dataset.bancada; estado.visibles = 40;
    $('select[name="tema"]').value = estado.tema; $('select[name="bancada"]').value = estado.bancada;
    location.hash = "#/";
    setTimeout(() => $("#t-explorar").scrollIntoView({ behavior: "smooth" }), 50);
  }));

  const sem_ = {};
  P.forEach((p) => {
    const d = new Date(p.fecha + "T00:00:00"); d.setDate(d.getDate() - ((d.getDay() + 6) % 7));
    const k = d.toISOString().slice(0, 10); sem_[k] = (sem_[k] || 0) + 1;
  });
  const ks = Object.keys(sem_).sort(); const mx = Math.max(...Object.values(sem_));
  $("#semanas").innerHTML = ks.map((k) => `<div style="height:${(sem_[k] / mx) * 100}%" title="Semana del ${fecha(k)}: ${sem_[k]} proyectos"><span>${sem_[k]}</span></div>`).join("");
}

iniciar();
