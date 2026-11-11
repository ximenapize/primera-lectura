// Primera Lectura — sitio estático. Lee site/data/*.json (los genera scripts/exportar_web.py).
"use strict";

const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const sinTildes = (s) => String(s ?? "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();

const SEMAFORO = { rojo: "Alerta roja", amarillo: "En observación", verde: "Sin riesgo relevante", sin: "Sin leer" };
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

const fechaLarga = (iso) => new Date(iso + "T12:00").toLocaleDateString("es-PE", { day: "numeric", month: "long" });
const camaraTxt = (c) => (c === "senado" ? "Senado" : "Cámara de Diputados");
// La explicación de la IA a veces nombra las preguntas de la rúbrica por su código interno: se cambian por palabras.
const CODIGOS = { contra_constitucion: "contra la Constitución", contra_tratado: "contra un tratado", no_proporcional: "proporcionalidad",
  equilibrio_poderes: "equilibrio de poderes", reglas_electorales: "reglas electorales", rendicion_cuentas: "rendición de cuentas",
  espacio_civico: "espacio cívico", sin_consulta: "consulta previa", gasto_sin_fondos: "gasto sin fondos",
  impacto_ambiental: "impacto ambiental", formula_legal: "fórmula legal" };
const codigos = (t) => String(t ?? "").replace(/\b[a-z]+(?:_[a-z]+)+\b/g, (m) => CODIGOS[m] || m.replaceAll("_", " "));
// La explicación del agente trae la jerga de la rúbrica ("Sí en restringe, regresiva: …"). Las respuestas ya se muestran
// aparte, así que aquí se quitan esas etiquetas y queda la explicación en prosa.
const limpio = (t) => {
  let s = codigos(String(t ?? "").replace(/formula_legal vac/gi, "FORMULA vac"))
    .replace(/FORMULA vac[ií]a: cita vac[ií]a; revisi[oó]n basada en/gi, "La fórmula legal viene vacía; la lectura se basa en")
    .replace(/(^|[.;]\s+)(?:S[ií]|Depende|Respuesta '?depende'?) en [^:.]{1,120}:\s*/g, "$1")
    .replace(/\s*\((?:[a-z_]+(?::\s*(?:s[ií]|no|depende))?(?:,\s*)?)+\)/g, "");
  s = s.replace(/Depende en contra (?:la )?Constituci[oó]n/g, "Su choque con la Constitución depende")
    .replace(/Es s[ií] en [^:.]{1,120}:\s*/g, "")
    .replace(/(^|\.\s+)([a-záéíóúñ])/g, (m, a, b) => a + b.toUpperCase());
  return s.replace(/FORMULA/g, "fórmula legal");
};
const minus = (s) => s[0].toLowerCase() + s.slice(1);
// Nombre corto de cada pregunta de la rúbrica, para las etiquetas del reporte.
const CORTO = { vulnerables: "Grupos vulnerables", restringe: "Restringe un derecho", no_proporcional: "Falla el test de proporcionalidad",
  regresiva: "Regresiva", contra_constitucion: "Contra la Constitución", contra_tratado: "Contra un tratado",
  equilibrio_poderes: "Equilibrio de poderes", reglas_electorales: "Reglas electorales", rendicion_cuentas: "Rendición de cuentas",
  espacio_civico: "Espacio cívico", sin_consulta: "Sin consulta previa", retroactiva: "Retroactiva",
  gasto_sin_fondos: "Gasto sin fondos", impacto_ambiental: "Impacto ambiental" };

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
  prepararReporte();
  window.addEventListener("hashchange", ruta);
  ruta();
}

// ---------------- rutas ----------------
const VISTAS = ["inicio", "reporte", "proyectos", "votaciones", "panorama", "como-funciona", "cliente"];
let vistaActual = "inicio";

function ruta() {
  const [seccion, id] = location.hash.replace(/^#\/?/, "").split("/");
  // la ficha se abre encima de la vista en la que estabas
  if (seccion === "p" && id) { mostrar(vistaActual); abrirFicha(decodeURIComponent(id)); return; }
  if ($("#ficha").open) $("#ficha").close();
  mostrar(VISTAS.includes(seccion) ? seccion : "inicio");
}

function mostrar(vista) {
  const cambia = $$(".vista").some((v) => !v.hidden && v.id !== `vista-${vista}`);
  vistaActual = vista;
  $$(".vista").forEach((v) => (v.hidden = v.id !== `vista-${vista}`));
  if (cambia) window.scrollTo(0, 0);
  $$(".barra nav a").forEach((a) => (a.dataset.ruta === vista ? a.setAttribute("aria-current", "page") : a.removeAttribute("aria-current")));
  if (vista === "proyectos") pintarLista();
  if (vista === "votaciones") pintarVotaciones();
  if (vista === "panorama") pintarPanorama();
  document.body.classList.toggle("modo-cliente", vista === "cliente" && sesion());
  if (vista === "cliente") pintarCliente();
}

// ---------------- hemiciclo: un punto por congresista, agrupados por bancada ----------------
const VOTO_TXT = { SI: "Sí", NO: "No", "Abst.": "Abstención", SinRes: "Sin respuesta", AUS: "Ausente", "***": "Presidía (no vota)" };
const claseVoto = (c) => (c === "SI" ? "SI" : c === "NO" ? "NO" : c.startsWith("Abst") ? "AB" : "AU");

// colores de cada bancada (los que reconoce el público) y orden en que se sientan, de izquierda a derecha
const COLOR_B = { FP: "#F28C00", AN: "#D7263D", RP: "#3AA6DD", OBRAS: "#1E7B3C", PBG: "#F2C200", JP: "#8CCB4E" };
const ORDEN_B = ["JP", "AN", "PBG", "OBRAS", "RP", "FP"];
const colorB = (s) => COLOR_B[s] || "#9AA3AE";
const siglaDe = (nombre) => Object.keys(META.bancadas || {}).find((k) => META.bancadas[k] === nombre) || "";
const chipB = (nombre) => (nombre ? `<span class="chip-b"><i style="background:${colorB(siglaDe(nombre))}"></i>${esc(nombre)}</span>` : "");
const posB = (s) => (ORDEN_B.includes(s) ? ORDEN_B.indexOf(s) : 99);
const FORMA_VOTO = `<div class="forma-voto"><span><i class="f-si"></i>A favor</span><span><i class="f-no"></i>En contra</span><span><i class="f-ab"></i>Abstención</span><span><i class="f-au"></i>Sin voto</span></div>`;
function composicionHTML(v) {
  const c = {};
  v.votos.forEach(([, b]) => (c[b] = (c[b] || 0) + 1));
  return Object.keys(c).sort((a, b) => posB(a) - posB(b))
    .map((b) => `<div style="border-color:${colorB(b)}"><b>${c[b]}</b>${esc(NOMBRE(b))}</div>`).join("");
}

function hemiHTML(v) {
  const votos = [...v.votos].sort((a, b) => posB(a[1]) - posB(b[1]) || a[1].localeCompare(b[1]) || a[0].localeCompare(b[0]));
  const n = votos.length;
  // filas en arco: cada una recibe asientos en proporción a su radio
  const radios = n > 80 ? [110, 140, 170, 200, 230, 260] : [140, 180, 220, 260];
  const suma = radios.reduce((a, r) => a + r, 0);
  let quedan = n, sillas = [];
  radios.forEach((r, i) => {
    const k = i === radios.length - 1 ? quedan : Math.round((n * r) / suma);
    quedan -= k;
    for (let j = 0; j < k; j++) { const a = (Math.PI * (j + 0.5)) / k; sillas.push({ a, x: 300 - r * Math.cos(a), y: 290 - r * Math.sin(a) }); }
  });
  // al ordenar los asientos por ángulo, cada bancada queda junta, como una cuña
  sillas.sort((p, q) => p.a - q.a);
  const puntos = sillas.map((s, i) => {
    const [nombre, b, c] = votos[i], t = claseVoto(c), col = colorB(b), r = n > 80 ? 8.5 : 11;
    // a favor: lleno; en contra: anillo; abstención: tenue; sin voto: punto gris chico
    const forma = t === "NO" ? `r="${r - 1.6}" style="fill:#fff;stroke:${col};stroke-width:3.2"`
      : t === "AU" ? `r="3.4" style="fill:#A3A9B3"` : `r="${r}" style="fill:${col}${t === "AB" ? ";fill-opacity:.32" : ""}"`;
    return `<circle cx="${s.x.toFixed(1)}" cy="${s.y.toFixed(1)}" ${forma} class="v-${t}" data-b="${esc(b)}"><title>${esc(nombre)} (${esc(NOMBRE(b))}): ${esc(VOTO_TXT[c] || "Con licencia")}</title></circle>`;
  }).join("");
  return `<svg class="hemi" viewBox="0 0 600 305" role="img" aria-label="Hemiciclo: ${esc(v.si || 0)} a favor, ${esc(v.no || 0)} en contra, ${esc(v.abst || 0)} abstenciones">${puntos}</svg>`;
}


// ---------------- señales del recorrido: qué tan rápido avanza y qué cambió en el dictamen ----------------
// Salen del texto de cada movimiento del expediente (Junta de Portavoces, dictámenes, exoneraciones).
function senales(p) {
  const s = [], todo = p.recorrido.map(([, , d]) => d.toUpperCase()).join(" | ");
  if (/CARÁCTER DE URGENTE/.test(todo)) s.push(["acelera", "La Junta de Portavoces le dio carácter de urgente"]);
  if (/EXONER/.test(todo)) s.push(["acelera", "Exonerado de un plazo o trámite"]);
  if (/AMPLIACIÓN DE AGENDA/.test(todo)) s.push(["acelera", "Entró por ampliación de agenda"]);
  if (/DISPENS/.test(todo)) s.push(["acelera", "Dispensado de un trámite"]);
  if (/POR UNANIMIDAD/.test(todo)) s.push(["info", "Dictamen aprobado por unanimidad"]);
  else if (/EN MAYORÍA/.test(todo)) s.push(["info", "Dictamen aprobado en mayoría"]);
  if (/SEGUNDA COMISI/.test(todo)) s.push(["frena", "Pasó a una segunda comisión"]);
  return s;
}
const acelera = (p) => senales(p).some(([t]) => t === "acelera");
// título del texto sustitutorio que aprobó la comisión, si lo hay
function tituloDictamen(p) {
  for (const [, , d] of p.recorrido) {
    const m = d.match(/FÓRMULA SUSTITUTORIA\s*-\s*(.+?)(?:\s*-\s*LA JUNTA|\.?\s*$)/i);
    if (m) return m[1].replace(/\s*\(DERIVAD[^)]*\)/i, "").trim();
  }
  return "";
}
function enAgendaDesde(p) {
  const f = p.recorrido.filter(([, e]) => /AGENDA/i.test(e)).map(([fe]) => fe).sort()[0];
  return f ? fechaLarga(f) : "";
}
function senalesHTML(p) {
  const s = senales(p);
  return s.length ? `<ul class="senales">${s.map(([t, x]) => `<li class="${t}">${esc(x)}</li>`).join("")}</ul>` : "";
}

// ---------------- reporte de la semana (inicio) ----------------
let votoSala = null, ROJAS = [], OBSERVACION = [];
const plDe = (v) => P.find((p) => p.camara === v.camara && p.pl === v.pls[0]);
const numPL = (v) => v.pls.map((x) => x.replace(/^0+/, "").replace(/-2026-2031.*/, "")).join(", ");

function prepararReporte() {
  const hasta = new Date(META.actualizado + "T12:00");
  const desde = new Date(hasta); desde.setDate(hasta.getDate() - 6);
  const semana = P.filter((p) => new Date(p.fecha + "T12:00") >= desde);
  const cuenta = (lista, color) => lista.filter((p) => sem(p) === color).length;
  $("#reporte-periodo").textContent = `Del ${fechaLarga(desde.toISOString().slice(0, 10))} al ${fechaLarga(META.actualizado)} de 2026. Diputados y Senado.`;
  const rojasSemana = cuenta(semana, "rojo");
  $("#reporte-semana").innerHTML = `Esta semana se presentaron <b>${semana.length} proyectos de ley</b>. ` +
    `${rojasSemana ? `${rojasSemana} ${rojasSemana === 1 ? "encendió" : "encendieron"} una alerta roja` : "Ninguno encendió una alerta roja"}, ` +
    `${cuenta(semana, "amarillo")} quedaron en observación, ${cuenta(semana, "verde")} no tocan derechos y ${cuenta(semana, "sin")} esperan su lectura. ` +
    `Abajo, las alertas que siguen vivas en el Congreso, de esta semana y de las anteriores.`;
  $("#bajada").textContent = `${P.length} proyectos de Diputados y Senado, actualizados cada día. La IA ya leyó el articulado de ${META.n_lecturas}; cada alerta trae la cita del artículo que la sustenta.`;

  // primero las alertas con más sustento: revisadas por el agente y con la cita verificada en el PDF
  const sustento = (p) => (p.lectura.por === "agente" ? 2 : 0) + (p.lectura.cita_ok ? 1 : 0);
  const orden = (a, b) => sustento(b) - sustento(a) || b.avance - a.avance || b.fecha.localeCompare(a.fecha);
  ROJAS = P.filter((p) => sem(p) === "rojo" && p.avance > 0).sort(orden);
  const amarillas = P.filter((p) => sem(p) === "amarillo" && p.avance > 0);
  OBSERVACION = amarillas.sort((a, b) => sustento(b) - sustento(a) || b.fecha.localeCompare(a.fecha)).slice(0, 6);
  const pesoColor = { rojo: 0, amarillo: 1, sin: 2, verde: 3 };
  const AGENDA = P.filter((p) => p.avance === 4).sort((a, b) => pesoColor[sem(a)] - pesoColor[sem(b)] || acelera(b) - acelera(a));
  $("#t-agenda").textContent = `En la agenda del Pleno (${AGENDA.length})`;
  $("#reporte-agenda").innerHTML = AGENDA.length ? AGENDA.map((p) => `<li>
      <span class="semaforo ${sem(p)}"><i class="punto ${sem(p)}"></i>${SEMAFORO[sem(p)]}</span>
      <a href="#/p/${encodeURIComponent(p.id)}">${esc(p.lectura?.resumen || oracion(p.titulo))}</a>
      <span class="agenda-meta">${chipB(p.bancada)} PL ${esc(codigo(p))}. En agenda desde el ${enAgendaDesde(p)}.</span>
      ${senalesHTML(p)}</li>`).join("") : "<li>No hay proyectos en la agenda del Pleno esta semana.</li>";
  $("#t-rojas").textContent = `Alertas rojas que siguen vivas (${ROJAS.length})`;
  $("#reporte-rojas").innerHTML = ROJAS.map(itemHTML).join("");
  $("#t-observacion").textContent = `En observación: ${OBSERVACION.length} de ${amarillas.length}`;
  $("#reporte-observacion").innerHTML = OBSERVACION.map(itemHTML).join("");

  // al abrir una alerta, el hemiciclo muestra a la bancada que la presentó
  $(".reporte").addEventListener("click", (e) => {
    const b = e.target.closest(".item-abre");
    if (!b) return;
    const item = b.closest(".item"), ya = item.classList.contains("activo");
    $$(".item.activo").forEach((x) => { x.classList.remove("activo"); $(".item-abre", x).setAttribute("aria-expanded", "false"); });
    if (ya) { salaVoto(); return; }
    item.classList.add("activo"); b.setAttribute("aria-expanded", "true");
    salaBancada(P.find((p) => p.id === item.dataset.id));
  });
  $("#reporte-pdf").addEventListener("click", () => window.print());

  // votaciones nominales para el hemiciclo; por defecto, la más dividida entre las rechazadas
  const nominales = V.filter((v) => v.tipo === "Votación" && v.votos.length).sort((a, b) => b.fecha.localeCompare(a.fecha));
  const dividida = (v) => Math.min(+v.si || 0, +v.no || 0);
  const rechazadas = nominales.filter((v) => v.resultado !== "Aprobado" && v.camara === "diputados");
  votoSala = (rechazadas.length ? rechazadas : nominales).reduce((m, v) => (dividida(v) > dividida(m) ? v : m));
  $("#elige-voto").innerHTML = nominales.map((v) => `<option value="${esc(v.id)}" ${v === votoSala ? "selected" : ""}>${fechaLarga(v.fecha)}, ${v.camara === "senado" ? "Senado" : "Diputados"}, PL ${esc(numPL(v))}: ${esc(v.resultado)} (${esc(v.si || 0)} a ${esc(v.no || 0)})</option>`).join("");
  $("#elige-voto").addEventListener("change", (e) => { votoSala = V.find((v) => String(v.id) === e.target.value); salaVoto(); });
  $("#modo-voto").addEventListener("click", salaVoto);
  $("#modo-bancada").addEventListener("click", () => salaBancada(null));
  if (votoSala) salaVoto();
  prepararInicio();
}

// ---------------- portada de empresa ----------------
function prepararInicio() {
  if (votoSala) {
    $("#heroe-hemi").innerHTML = hemiHTML(votoSala);
    $("#heroe-comp").innerHTML = composicionHTML(votoSala);
    $("#heroe-forma").innerHTML = FORMA_VOTO;
    const aprob = votoSala.resultado === "Aprobado";
    $("#heroe-pie").textContent = `Así votó ${votoSala.camara === "senado" ? "el Senado" : "Diputados"} el PL ${numPL(votoSala)} el ${fechaLarga(votoSala.fecha)}: ` +
      `${votoSala.si || 0} a favor, ${votoSala.no || 0} en contra. ${aprob ? "Aprobado" : "Rechazado"}. Un punto por congresista.`;
  }
  const leidas = P.filter((p) => p.lectura).length;
  $("#cifras").innerHTML = [
    [P.length, `proyectos de ley presentados entre el 4 de agosto y el ${fechaLarga(META.actualizado)}`],
    ["9", "proyectos nuevos al día, cada uno un PDF de 10 a 25 páginas"],
    [leidas, "proyectos leídos completos por la IA, con la cita verificada"],
    [ROJAS.length, "alertas rojas que siguen vivas en el Congreso"],
  ].map(([n, t]) => `<div><b>${esc(n)}</b><span>${esc(t)}</span></div>`).join("");
  $("#muestra-alertas").innerHTML = ROJAS.slice(0, 3).map((p) => `<article>
      <p class="etiqueta-riesgo">Alerta roja</p>
      <h3><a href="#/p/${encodeURIComponent(p.id)}">${esc(p.lectura.resumen || oracion(p.titulo))}</a></h3>
      <p class="muestra-meta">${chipB(p.bancada)} PL ${esc(codigo(p))}, ${p.camara === "senado" ? "Senado" : "Diputados"}. ${esc(AVANCE[p.avance])}.</p>
    </article>`).join("");
}

function itemHTML(p) {
  const l = p.lectura;
  const activas = Object.entries(l.preguntas || {}).filter(([, r]) => r === "si" || r === "depende");
  return `<article class="item" data-id="${esc(p.id)}">
    <div class="item-cab"><span class="etiqueta-riesgo ${esc(l.semaforo)}">${l.semaforo === "rojo" ? "Alerta roja" : "En observación"}</span>
      ${chipB(p.bancada)}<span>PL ${esc(codigo(p))}, ${p.camara === "senado" ? "Senado" : "Diputados"}</span><span>${esc(AVANCE[p.avance])}</span></div>
    <h4><button type="button" class="item-abre" aria-expanded="false">${esc(l.resumen || oracion(p.titulo))}</button></h4>
    <div class="item-cuerpo">
      ${citaHTML(l)}
      <p>${esc(limpio(l.explicacion))}</p>
      ${activas.length ? `<p class="activa">Lo que marcó la rúbrica: ${activas.map(([k, r]) => r === "si" ? `<b>${esc(minus(CORTO[k] || k))}</b>` : `${esc(minus(CORTO[k] || k))} (depende)`).join(", ")}.</p>` : ""}
      ${l.ganan || l.pierden ? `<div class="gp"><div><h5>Quiénes ganan</h5><p>${esc(l.ganan || "Sin dato")}</p></div><div><h5>Quiénes pierden</h5><p>${esc(l.pierden || "Sin dato")}</p></div></div>` : ""}
      <div class="item-acciones"><button type="button" class="boton-sec" data-abrir="${esc(p.id)}">Abrir la ficha completa</button>
        <a href="${esc(p.url)}" target="_blank" rel="noopener">Expediente en el portal del Congreso</a></div>
    </div>
  </article>`;
}

function salaVoto() {
  const v = votoSala, p = plDe(v), aprob = v.resultado === "Aprobado";
  const [mas, menos] = aprob ? [v.si, v.no] : [v.no, v.si];
  $("#sala-titulo").textContent = `${v.camara === "senado" ? "El Senado" : "Diputados"} ${aprob ? "aprobó" : "rechazó"} el PL ${numPL(v)} por ${mas || 0} votos contra ${menos || 0}`;
  const mov = oracion(v.movimiento).replace(/\.$/, "");
  $("#sala-sub").textContent = `${p ? (p.lectura?.resumen || oracion(p.titulo)).replace(/\.$/, "") + ". " : ""}Votación del ${fechaLarga(v.fecha)}.`;
  $("#sala-sub").title = mov;
  $("#sala-hemi").innerHTML = hemiHTML(v);
  const otros = v.votos.length - (+v.si || 0) - (+v.no || 0) - (+v.abst || 0);
  $("#sala-marcador").innerHTML = [["si", v.si, "a favor"], ["no", v.no, "en contra"], ["ab", v.abst, "abstenciones"], ["au", otros, "sin voto"]]
    .map(([c, n, t]) => `<div><i class="f-${c}"></i><b>${esc(n || 0)}</b><span>${t}</span></div>`).join("");
  $("#sala-comp").innerHTML = composicionHTML(v);
  $("#modo-voto").setAttribute("aria-pressed", "true"); $("#modo-bancada").setAttribute("aria-pressed", "false");
}

// p = proyecto abierto en el reporte; sin p, se encienden todas las bancadas con alertas rojas
function salaBancada(p) {
  const v = votoSala;
  if (!$("#sala-hemi .hemi")) $("#sala-hemi").innerHTML = hemiHTML(v);
  const sigla = (nombre) => Object.keys(META.bancadas).find((k) => META.bancadas[k] === nombre);
  const porBancada = {};
  ROJAS.forEach((x) => (porBancada[x.bancada] = (porBancada[x.bancada] || 0) + 1));
  const prendidas = p ? [sigla(p.bancada)] : Object.keys(porBancada).map(sigla);
  let m = 0;
  $("#sala-hemi .hemi").classList.add("por-bancada");
  $$("#sala-hemi circle").forEach((c) => { const on = prendidas.includes(c.dataset.b); m += on; c.classList.toggle("on", on); });
  const donde = `${v.votos.length} escaños ${v.camara === "senado" ? "del Senado" : "de Diputados"}`;
  if (p) {
    const roja = sem(p) === "rojo";
    const suyas = roja ? porBancada[p.bancada] || 0 : P.filter((x) => sem(x) === "amarillo" && x.avance > 0 && x.bancada === p.bancada).length;
    $("#sala-titulo").textContent = roja ? `${p.bancada}: ${suyas} de las ${ROJAS.length} alertas rojas abiertas` : `${p.bancada}: ${suyas} proyectos en observación`;
    $("#sala-sub").textContent = m ? `La bancada ocupa ${m} de los ${donde}. Abre otra alerta del reporte para ver a su bancada.`
      : "Este proyecto viene de un grupo sin escaños en esta cámara, o lo firman varias bancadas.";
  } else {
    const lista = Object.entries(porBancada).sort((a, b) => b[1] - a[1]);
    $("#sala-titulo").textContent = `Las ${ROJAS.length} alertas rojas vienen de ${lista.length} ${lista.length === 1 ? "bancada" : "bancadas"}`;
    $("#sala-sub").textContent = `${lista.map(([b, n]) => `${b}: ${n}`).join(". ")}. Juntas ocupan ${m} de los ${donde}. Abre una alerta del reporte para ver solo a su bancada.`;
  }
  $("#sala-marcador").innerHTML = "";
  $("#modo-voto").setAttribute("aria-pressed", "false"); $("#modo-bancada").setAttribute("aria-pressed", "true");
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
          <span class="fila-datos">${chipB(p.bancada)}<span>${esc(p.tema)}</span></span>
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

// ---------------- checklist de la rúbrica ----------------
const RESP = { si: "Sí", no: "No", depende: "Depende", no_aplica: "No aplica" };
function checklistHTML(l) {
  if (!l.preguntas || !META.preguntas) return "";
  const fila = (q) => {
    const r = l.preguntas[q.id] || "no_aplica";
    return `<li class="preg ${r}"><span class="resp">${RESP[r]}</span><span>${esc(q.texto)}${q.critica ? ' <b class="critica">crítica</b>' : ""}</span></li>`;
  };
  const activas = META.preguntas.filter((q) => ["si", "depende"].includes(l.preguntas[q.id]));
  return `<div class="checklist">
    <h4>Preguntas de la rúbrica que se activaron</h4>
    ${activas.length ? `<ul>${activas.map(fila).join("")}</ul>` : `<p class="totales">Ninguna: todas las respuestas son "no" o "no aplica".</p>`}
    <details><summary>Ver las ${META.preguntas.length} preguntas</summary><ul>${META.preguntas.map(fila).join("")}</ul></details>
  </div>`;
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
        <span class="lectura-por">${l.por === "agente" ? (l.preguntas ? "Segunda lectura con la rúbrica (Claude Sonnet)" : "Segunda lectura: revisada por el agente") : `Primera lectura: modelo local ${esc((l.modelo || "qwen2.5:7b").replace(":", " "))}`}</span>
      </div>
      <p class="resumen">${esc(l.resumen)}</p>
      ${citaHTML(l)}
      <p>${esc(limpio(l.explicacion))}</p>
      ${l.ganan || l.pierden ? `<dl class="ganan"><dt>Ganan</dt><dd>${esc(l.ganan || "Sin dato")}</dd><dt>Pierden</dt><dd>${esc(l.pierden || "Sin dato")}</dd></dl>` : ""}
      ${checklistHTML(l)}
      ${l.derechos.length ? `<div class="etiquetas">${l.derechos.map((d) => `<span>${esc(d)}</span>`).join("")}</div>` : ""}
      ${l.estandares.length ? `<ul class="estandares">${l.estandares.map((s) => `<li>${esc(s)}</li>`).join("")}</ul>` : ""}
      ${l.revisar ? `<p class="aviso-revisar">El sustento de esta lectura está incompleto; está en cola para la segunda lectura.</p>` : ""}
    </section>` : `<p class="sin-lectura">La IA todavía no leyó este proyecto: no pasó el filtro de temas sensibles o está en cola.</p>`;

  const votos = V.filter((v) => v.camara === p.camara && v.pls.includes(p.pl));
  const datos = [["Temática", p.tema + (p.temas2 ? ` (también: ${p.temas2})` : "")], ["Bancada", p.bancada], ["Autor", p.autor],
    ["Coautores", p.coautores.replaceAll("; ", ", ")], ["Comisión", p.comision], ["Estado", p.estado]].filter(([, v]) => v);

  $("#ficha-contenido").innerHTML = `
    <div class="ficha-cabeza">
      <div><p>PL ${esc(codigo(p))}, ${p.camara === "senado" ? "Senado" : "Cámara de Diputados"}, presentado el ${fecha(p.fecha)}</p></div>
      <div class="ficha-botones">${sesion() ? `<button class="boton-sec" type="button" id="ficha-seguir">${seguidos().includes(p.id) ? "Dejar de seguir" : "Seguir este proyecto"}</button>` : ""}<button class="boton-pri" type="button" id="ficha-pdf">Descargar PDF</button>
        <button class="cerrar" type="button" aria-label="Cerrar la ficha" id="cerrar">${ICONO.cerrar}</button></div>
    </div>
    <h2 class="titulo-ley" id="ficha-titulo">${esc(oracion(p.titulo))}</h2>
    ${p.avance ? `<ol class="ruta" aria-label="Avance del proyecto">${[1, 2, 3, 4, 5].map((i) => `<li class="${p.avance >= i ? "hecho" : ""} ${p.avance === i ? "actual" : ""}">${AVANCE[i]}</li>`).join("")}</ol>` : `<p class="ruta-archivado">Archivado o retirado.</p>`}
    ${senales(p).length || tituloDictamen(p) ? `<section class="avanza"><h3>Cómo avanza</h3>${senalesHTML(p)}
      ${tituloDictamen(p) ? `<div class="cambio"><p><b>Qué cambió en el dictamen.</b> La comisión aprobó un texto sustitutorio, distinto al que se presentó.</p>
        <dl><dt>Se presentó como</dt><dd>${esc(oracion(p.titulo))}</dd><dt>La comisión lo aprobó como</dt><dd>${esc(oracion(tituloDictamen(p)))}</dd></dl>
        <p class="nota">La comparación artículo por artículo entre los dos textos viene en la próxima versión.</p></div>` : ""}</section>` : ""}
    ${lectura}
    ${votos.length ? `<section><h3>Cómo se votó en el Pleno</h3>${votos.map(votoHTML).join("")}</section>` : ""}
    <section><h3>Sumilla</h3><p>${esc(oracion(p.sumilla))}</p></section>
    <dl class="datos">${datos.map(([k, v]) => `<dt>${k}</dt><dd>${esc(v)}</dd>`).join("")}</dl>
    <div class="enlaces">
      <a href="${esc(p.pdf)}" target="_blank" rel="noopener">${ICONO.pdf}PDF del proyecto</a>
      <a href="${esc(p.url)}" target="_blank" rel="noopener">${ICONO.externo}Expediente en el portal del Congreso</a>
    </div>
    <section><h3>Recorrido</h3><ol class="recorrido">${p.recorrido.map(([f, e, d]) =>
      `<li><time>${fecha(f)}</time><b>${esc(e)}</b>${d ? `<br>${esc(d)}` : ""}</li>`).join("")}</ol></section>`;

  const dlg = $("#ficha");
  if (!dlg.open) dlg.showModal();
  dlg.scrollTop = 0;
  $("#cerrar").addEventListener("click", () => dlg.close());
  $("#ficha-seguir")?.addEventListener("click", (e) => {
    const s = seguidos(), ya = s.includes(p.id);
    guardar("pl-seguidos", ya ? s.filter((x) => x !== p.id) : [...s, p.id]);
    e.target.textContent = ya ? "Seguir este proyecto" : "Dejar de seguir";
    if (vistaActual === "cliente") pintarCliente();
  });
  $("#ficha-pdf").addEventListener("click", () => {
    document.body.classList.add("imprime-ficha");
    window.print();
  });
}

$("#ficha").addEventListener("close", () => {
  if (location.hash.startsWith("#/p/")) history.replaceState(null, "", vistaActual === "inicio" ? "#/" : `#/${vistaActual}`);
});
window.addEventListener("afterprint", () => document.body.classList.remove("imprime-ficha"));
$("#ficha").addEventListener("click", (e) => { if (e.target.id === "ficha") e.target.close(); });

// ---------------- votaciones ----------------
const NOMBRE = (s) => META.bancadas?.[s] || s;

function votoHTML(v) {
  const aprob = v.resultado === "Aprobado";
  const filas = v.bancadas ? Object.entries(v.bancadas).map(([b, n]) => {
    const total = n.reduce((a, x) => a + x, 0) || 1;
    const seg = ["si", "no", "abst", "sr"].map((c, i) => n[i] ? `<span class="c-${c}" style="width:${(n[i] / total) * 100}%" title="${n[i]}"></span>` : "").join("");
    return `${chipB(NOMBRE(b))}<span class="barra-v" role="img" aria-label="${esc(NOMBRE(b))}: ${n[0]} sí, ${n[1]} no, ${n[2]} abstenciones">${seg}</span><span>${n[0]}/${total}</span>`;
  }).join("") : "";
  return `<div class="voto">
    <div class="voto-cabeza"><span class="resultado ${aprob ? "si" : "no"}">${esc(v.resultado || "Sin resultado")}</span><span class="totales">${fecha(v.fecha)}</span></div>
    <p>${esc(oracion(v.movimiento))}</p>
    <p class="totales">A favor ${esc(v.si || "—")}, en contra ${esc(v.no || "—")}, abstenciones ${esc(v.abst || "—")}</p>
    ${v.votos?.length ? hemiHTML(v) + FORMA_VOTO : ""}
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
  $("#cohesion").innerHTML = bancadas.map((b) => `<div class="barra-h">${chipB(NOMBRE(b))}
    <span class="pista"><span style="width:${avg(coh[b]) * 100}%;background:${colorB(b)}"></span></span><b>${Math.round(avg(coh[b]) * 100)}%</b></div>`).join("");

  const n = bancadas.length;
  let m = `<div></div>` + bancadas.map((b) => `<div class="rot" title="${esc(NOMBRE(b))}"><i style="background:${colorB(b)}"></i>${esc(b)}</div>`).join("");
  bancadas.forEach((a) => {
    m += `<div class="rot" title="${esc(NOMBRE(a))}"><i style="background:${colorB(a)}"></i>${esc(b2(a))}</div>`;
    bancadas.forEach((b) => {
      const ids = Object.keys(pos[a] || {}).filter((id) => pos[b]?.[id]);
      const pct = ids.length ? ids.filter((id) => pos[a][id] === pos[b][id]).length / ids.length : 0;
      const fondo = `rgba(31,63,110,${0.08 + pct * 0.85})`;
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
    const filas = vs.map((v) => [v, v.votos.find(([x]) => x === c)]).filter(([, x]) => x);
    $("#historial").innerHTML = `<table><thead><tr><th>Fecha</th><th>Proyecto y votación</th><th>Voto</th></tr></thead><tbody>${filas.map(([v, x]) =>
      `<tr><td>${fecha(v.fecha)}</td><td>PL ${esc(v.pls.join(", "))}: ${esc(oracion(v.movimiento))}</td><td><b>${esc(VOTO_TXT[x[2]] || "Con licencia")}</b></td></tr>`).join("")}</tbody></table>`;
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
      return `<td><button type="button" data-tema="${esc(t)}" data-bancada="${esc(b)}" style="background:rgba(31,63,110,${a});color:${n / max > 0.5 ? "#fff" : "var(--tinta)"}" aria-label="${n} proyectos de ${esc(t)} de ${esc(b)}">${n || ""}</button></td>`;
    }).join("")}</tr>`).join("")}</tbody></table>`;
  $$("#mapa-calor button").forEach((b) => b.addEventListener("click", () => {
    estado.tema = b.dataset.tema; estado.bancada = b.dataset.bancada; estado.visibles = 40;
    $('select[name="tema"]').value = estado.tema; $('select[name="bancada"]').value = estado.bancada;
    location.hash = "#/proyectos";
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


// ---------------- espacio del cliente (demo) ----------------
// Es un sitio estático: no hay servidor ni cuentas reales. El acceso se simula en el navegador con una cuenta de
// demostración, para mostrar cómo vería el producto un cliente de pago.
const DEMO = { usuario: "observatorio", clave: "primeralectura", nombre: "Observatorio Demo" };
const guardado = (k, def) => { try { return JSON.parse(localStorage.getItem(k)) ?? def; } catch { return def; } };
const guardar = (k, v) => { try { localStorage.setItem(k, JSON.stringify(v)); } catch { /* sin almacenamiento: no pasa nada */ } };
const sesion = () => { try { return sessionStorage.getItem("pl-sesion") === "1"; } catch { return false; } };
const seguidos = () => guardado("pl-seguidos", [...ROJAS.slice(0, 3), ...P.filter((p) => p.avance === 4).slice(0, 2)].map((p) => p.id));

function pintarCliente() {
  const dentro = sesion();
  $("#acceso").hidden = dentro;
  $("#panel-cliente").hidden = !dentro;
  $("#acceso-demo").innerHTML = `Para la demostración: usuario <b>${DEMO.usuario}</b>, contraseña <b>${DEMO.clave}</b>.`;
  if (!dentro) return;
  $("#cl-nombre").textContent = DEMO.nombre;
  $("#cl-periodo").textContent = $("#reporte-periodo").textContent;
  const agenda = P.filter((p) => p.avance === 4).sort((a, b) => ({ rojo: 0, amarillo: 1, sin: 2, verde: 3 }[sem(a)] - { rojo: 0, amarillo: 1, sin: 2, verde: 3 }[sem(b)]));
  const mios = seguidos().map((id) => P.find((p) => p.id === id)).filter(Boolean);
  $("#cl-kpis").innerHTML = [[P.length, "proyectos en seguimiento"], [P.filter((p) => p.lectura).length, "leídos completos por la IA"],
    [ROJAS.length, "alertas rojas vivas", "al"], [agenda.length, "en la agenda del Pleno"], [mios.length, "proyectos que sigues"]]
    .map(([n, t, c]) => `<div class="cl-kpi ${c || ""}"><b>${n}</b><span>${t}</span></div>`).join("");
  const v = votoSala;
  if (v) {
    $("#cl-vt").textContent = `PL ${numPL(v)}: ${v.resultado === "Aprobado" ? "aprobado" : "rechazado"} ${v.no > v.si ? `${v.no} a ${v.si}` : `${v.si} a ${v.no}`}, ${fechaLarga(v.fecha)}`;
    $("#cl-hemi").innerHTML = hemiHTML(v) + FORMA_VOTO;
    const esc_ = {}; v.votos.forEach(([, b]) => (esc_[b] = (esc_[b] || 0) + 1));
    const cuenta = (b, c) => P.filter((p) => sem(p) === c && p.avance > 0 && siglaDe(p.bancada) === b).length;
    $("#cl-bancadas").innerHTML = Object.keys(esc_).sort((a, b) => posB(a) - posB(b)).map((b) =>
      `<tr><td>${chipB(NOMBRE(b))}</td><td class="n">${esc_[b]}</td><td class="n">${cuenta(b, "rojo") || "–"}</td><td class="n">${cuenta(b, "amarillo") || "–"}</td></tr>`).join("");
  }
  const etiqueta = (p) => `<span class="cl-tag ${sem(p)}">${{ rojo: "Alerta roja", amarillo: "Observación", verde: "Sin riesgo", sin: "Sin leer" }[sem(p)]}</span>`;
  const fila = (p, extra = "") => `<tr><td>${etiqueta(p)}${extra}</td><td><a href="#/p/${encodeURIComponent(p.id)}"><b>PL ${esc(codigo(p))}</b> ${esc(p.lectura?.resumen || oracion(p.titulo))}</a></td><td>${chipB(p.bancada)}</td></tr>`;
  $("#cl-filas").innerHTML = agenda.slice(0, 4).map((p) => fila(p, `<span class="cl-en-agenda">En agenda</span>`)).join("") + ROJAS.map((p) => fila(p)).join("");
  $("#cl-seguidos").innerHTML = mios.length ? mios.map((p) => {
    const [f, e] = p.recorrido.at(-1) || ["", ""];
    return `<tr><td><a href="#/p/${encodeURIComponent(p.id)}"><b>PL ${esc(codigo(p))}</b> ${esc(p.lectura?.resumen || oracion(p.titulo))}</a>${senalesHTML(p)}</td><td>${chipB(p.bancada)}</td>
      <td>${esc(AVANCE[p.avance])}</td><td>${fecha(f)}<br><span class="cl-sub">${esc(cap(e))}</span></td>
      <td><button type="button" class="enlace" data-dejar="${esc(p.id)}">Dejar de seguir</button></td></tr>`;
  }).join("") : `<tr><td colspan="5">Todavía no sigues ningún proyecto. Ábrelo desde el reporte y usa «Seguir este proyecto».</td></tr>`;
}

$("#form-acceso").addEventListener("submit", (e) => {
  e.preventDefault();
  const f = new FormData(e.target);
  if (f.get("usuario").trim().toLowerCase() === DEMO.usuario && f.get("clave") === DEMO.clave) {
    try { sessionStorage.setItem("pl-sesion", "1"); } catch { /* sigue en esta pestaña igual */ }
    $("#acceso-error").textContent = "";
    e.target.reset();
    mostrar("cliente");
  } else {
    $("#acceso-error").textContent = "El usuario o la contraseña no coinciden. Usa la cuenta de demostración que aparece abajo.";
  }
});
$("#cl-salir").addEventListener("click", () => { try { sessionStorage.removeItem("pl-sesion"); } catch {} mostrar("cliente"); });
$("#cl-pdf").addEventListener("click", () => window.print());
$("#cl-excel").addEventListener("click", () => {
  const filas = [["PL", "Camara", "Semaforo", "Resumen", "Bancada", "Etapa", "Enlace"],
    ...[...new Set([...seguidos(), ...ROJAS.map((p) => p.id)])].map((id) => P.find((p) => p.id === id)).filter(Boolean)
      .map((p) => [codigo(p), p.camara, sem(p), p.lectura?.resumen || p.titulo, p.bancada, AVANCE[p.avance], p.url])];
  const csv = "\ufeff" + filas.map((r) => r.map((x) => `"${String(x ?? "").replaceAll('"', '""')}"`).join(",")).join("\n");
  const a = Object.assign(document.createElement("a"), { href: URL.createObjectURL(new Blob([csv], { type: "text/csv" })), download: "primera-lectura-reporte.csv" });
  a.click();
});
$("#panel-cliente").addEventListener("click", (e) => {
  const b = e.target.closest("[data-dejar]");
  if (b) { guardar("pl-seguidos", seguidos().filter((id) => id !== b.dataset.dejar)); pintarCliente(); }
  const ancla = e.target.closest('.cl-lado nav a');
  if (ancla) { e.preventDefault(); $(ancla.getAttribute("href")).scrollIntoView({ behavior: "smooth", block: "start" }); }
});
