// Hemiciclo compartido por las tres maquetas: el color es la bancada; el voto es la forma.
// A favor = punto lleno, en contra = anillo, abstención = punto tenue, sin voto = punto gris chico.
window.COLOR = { FP: "#F28C00", AN: "#D7263D", RP: "#3AA6DD", OBRAS: "#1E7B3C", PBG: "#F2C200", JP: "#8CCB4E" };
window.ORDEN = ["JP", "AN", "PBG", "OBRAS", "RP", "FP"]; // de izquierda a derecha, como se sientan
function claseVoto(c) { return c === "SI" ? "si" : c === "NO" ? "no" : /^Abst/.test(c) ? "ab" : "au"; }
window.hemi = function (v, opt = {}) {
  const votos = [...v.votos].sort((a, b) => ORDEN.indexOf(a[1]) - ORDEN.indexOf(b[1]) || a[0].localeCompare(b[0]));
  const n = votos.length, radios = [110, 140, 170, 200, 230, 260], suma = radios.reduce((a, r) => a + r, 0);
  let quedan = n, sillas = [];
  radios.forEach((r, i) => {
    const k = i === radios.length - 1 ? quedan : Math.round((n * r) / suma); quedan -= k;
    for (let j = 0; j < k; j++) { const a = (Math.PI * (j + 0.5)) / k; sillas.push({ a, x: 300 - r * Math.cos(a), y: 290 - r * Math.sin(a) }); }
  });
  sillas.sort((p, q) => p.a - q.a);
  const r = 8.6, fondo = opt.fondo || "#fff";
  const pts = sillas.map((s, i) => {
    const [nom, b, c] = votos[i], col = COLOR[b] || "#888", t = claseVoto(c);
    const resalta = opt.solo && opt.solo !== b ? ' opacity="0.15"' : "";
    let dot;
    if (opt.modo === "bancada" || t === "si") dot = `<circle cx="${s.x.toFixed(1)}" cy="${s.y.toFixed(1)}" r="${r}" fill="${col}"${resalta}/>`;
    else if (t === "no") dot = `<circle cx="${s.x.toFixed(1)}" cy="${s.y.toFixed(1)}" r="${r - 1.6}" fill="${fondo}" stroke="${col}" stroke-width="3.2"${resalta}/>`;
    else if (t === "ab") dot = `<circle cx="${s.x.toFixed(1)}" cy="${s.y.toFixed(1)}" r="${r}" fill="${col}" opacity="0.32"/>`;
    else dot = `<circle cx="${s.x.toFixed(1)}" cy="${s.y.toFixed(1)}" r="3.4" fill="#A3A9B3"/>`;
    return dot.replace("/>", `><title>${nom} (${D.bancadas[b] || b})</title></circle>`);
  }).join("");
  return `<svg viewBox="0 0 600 300" class="hemi" role="img" aria-label="Hemiciclo">${pts}</svg>`;
};
window.escanos = () => { const c = {}; D.voto.votos.forEach(([, b]) => (c[b] = (c[b] || 0) + 1)); return ORDEN.map((b) => [b, c[b] || 0]); };
window.chip = (nombre) => { const s = D.sigla[nombre] || ""; return `<span class="chip"><i style="background:${COLOR[s] || "#888"}"></i>${nombre}</span>`; };
window.fechaL = (d) => new Date(d + "T12:00").toLocaleDateString("es-PE", { day: "numeric", month: "long" });
