# votaciones.py
# Votaciones del Pleno vinculadas a cada proyecto de ley. Lee SOLO los PDF que el propio expediente adjunta en
# sus movimientos «ASISTENCIA Y VOTACIÓN - ...» (data/movimientos.csv, ver scripts/scraper.py): así cada
# votación queda unida a sus proposiciones sin adivinar. Reescribe e integra el pipeline anterior
# (clasificar página, identificar asunto, extraer votos, reconciliar votos orales) en un solo programa:
#   1. junta los PDF de votación de los expedientes (un mismo PDF puede servir a varias proposiciones)
#   2. lee cada página con coordenadas: texto nativo (pdfplumber) o, si es un escaneo, OCR (RapidOCR)
#   3. reconoce la plantilla de 3 columnas y la numerada de 2 columnas, y casa cada nombre con el maestro
#      de congresistas (data/maestro_congresistas.csv, una base aparte que arma scripts/maestro.py)
#   4. lee el cuadro de resultados impreso (totales y votos por bancada) y lo compara con lo leído
#   5. aplica las constancias de voto oral («deja constancia del voto a favor de los diputados...»)
#   6. las páginas sin tabla (actas del Senado o de Diputados) se guardan como «Nota» con su resultado
# Salidas (en data/):
#   votos.csv        una fila por congresista y página (asistencia o votación)
#   votaciones.csv   una fila por página: asunto, resultado impreso, votos por bancada y control de lectura
# Es incremental: el OCR y la lectura quedan en data/cache_votaciones/.
# Uso: uv run scripts/votaciones.py   (opciones: --sin-ocr, --forzar, --solo ID_ARCHIVO)
import argparse
import csv
import difflib
import hashlib
import json
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

import pdfplumber
import requests

RAIZ = Path(__file__).resolve().parents[1]
DATA = RAIZ / "data"
DIR_PDF = DATA / "pdf_votaciones"
DIR_CACHE = DATA / "cache_votaciones"
MAESTRO = DATA / "maestro_congresistas.csv"
MOVIMIENTOS = DATA / "movimientos.csv"
HEADERS = {"User-Agent": "Mozilla/5.0 (scrapeo academico)"}
VERSION_LECTOR = 1     # subir al cambiar la lógica de lectura: invalida la lectura en caché (no el OCR)
ESCALA_OCR = 300 / 72  # 300 dpi

# código del PDF -> texto. Une los vocabularios de la plantilla de 3 columnas y de la numerada.
ESTADOS = {
    "SI": "Sí", "NO": "No", "Abst.": "Abstención", "SinRes": "Sin respuesta", "***": "Presidencia (no vota)",
    "PRE": "Presente", "AUS": "Ausente", "SUS": "Suspendido", "SUSP": "Suspendido",
    "LE": "Licencia por enfermedad", "LO": "Licencia oficial", "LP": "Licencia personal",
    "LV": "Licencia por viaje", "LVO": "Licencia por viaje oficial", "LAP": "Licencia por asunto particular",
    "LSGH": "Licencia sin goce de haber", "L": "Licencia sin goce de haber", "LSC": "Licencia por sesión de comisión",
    "LMD": "Licencia por Mesa Directiva",
}
BANCADAS = {"FP": "FUERZAPOPULAR", "JP": "JUNTOSPORELPERU", "PBG": "PARTIDODELBUENGOBIERNO",
            "RP": "RENOVACIONPOPULAR", "AN": "AHORANACION", "OBRAS": "PARTIDOCIVICOOBRAS"}
SIGLAS = set(BANCADAS) | {"PCO"}  # el PDF usa PCO para Partido Cívico Obras; el maestro, OBRAS
ALIAS = {"DUARTEPATINODEPEZET": "Duarte, Georgina"}  # el acta usa un apellido más largo que el portal
TOTALES = [  # cuadro «Resultado» impreso al pie de la página
    (r"^AFAVOR\(?S[I1l]\)?(\d+)", "a_favor"), (r"^ENCONTRA\(?N[O0]\)?(\d+)", "en_contra"),
    (r"^ABSTENCI[O0]N(?:ES)?(\d+)", "abstencion"), (r"^SINRESPUESTA(\d+)", "sin_respuesta"),
    (r"^PRESENTES?(\d+)", "presentes"), (r"^AUSENTES?(\d+)", "ausentes"),
]


# ===================== Utilidades =====================
def clave(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().upper()
    return re.sub(r"[^A-Z]", "", s)


def sha(ruta: Path) -> str:
    return hashlib.sha256(ruta.read_bytes()).hexdigest()[:16]


def cargar_maestro() -> dict:
    """{camara: [{nombre, clave, bancada}]} desde la base aparte de congresistas."""
    por_camara = defaultdict(list)
    with open(MAESTRO, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            por_camara[r["camara"]].append({"nombre": r["congresista"], "clave": r["clave"], "bancada": r["bancada"]})
    return por_camara


def casar(nombre: str, lista: list):
    """Nombre leído (a veces cortado por el ancho de la columna o mal leído por OCR) -> (congresista, puntaje)."""
    k = clave(nombre)
    for prefijo, oficial in ALIAS.items():
        if k.startswith(prefijo):
            return next((d for d in lista if d["nombre"] == oficial), None), 1.0
    if len(k) < 6:
        return None, 0.0
    mejor, sc = None, 0.0
    for d in lista:
        corto = d["clave"][: len(k)]  # el PDF corta el nombre: se compara con el mismo largo
        r = 1.0 if corto == k else difflib.SequenceMatcher(None, k, corto).ratio()
        if r > sc:
            mejor, sc = d, r
    if sc >= 0.86:
        return mejor, sc
    # respaldo: el primer apellido, solo si es único en la cámara
    primer = clave(re.split(r"[ ,]", nombre.strip())[0]) if nombre.strip() else ""
    c = [d for d in lista if len(primer) >= 5 and d["clave"].startswith(primer)]
    return (c[0], 0.9) if len(c) == 1 else (None, sc)


def estado_de(tok: str, ocr: bool):
    """Token -> (código, confianza). Con OCR acepta confusiones típicas: S1/Sl por SI, N0 por NO, IS por SI."""
    t = tok.strip().rstrip(",.").strip()
    if t in ESTADOS:
        return t, 1.0
    t = re.sub(r"[-–—_]+$", "", t)  # «NO---»
    k = clave(t)
    exactos = {clave(e): e for e in ESTADOS if clave(e)}
    if k in exactos and len(k) >= 2:  # «Abst», «SÍ», «sinres»
        return exactos[k], 1.0
    if t == "P":  # la plantilla numerada marca «P» de presente
        return "PRE", 1.0
    if ocr:
        if re.fullmatch(r"[*★☆✱∗·•]{2,}", t):
            return "***", 0.95
        k2 = clave(t.translate(str.maketrans("1058l", "ISOBI")))
        for c in (k2, k2[::-1]):
            if c in exactos and len(c) == 2:
                return exactos[c], 0.9
    return None, 0.0


# ===================== Lectura de una página =====================
def filas_por_y(frags, tol=4.5):
    """Agrupa fragmentos [(x, y, texto)] en filas visuales (y cercanos), cada una ordenada por x."""
    filas, actual, ultimo = [], [], None
    for f in sorted(frags, key=lambda f: f[1]):
        if ultimo is not None and f[1] - ultimo > tol:
            filas.append(sorted(actual))
            actual = []
        actual.append(f)
        ultimo = f[1]
    if actual:
        filas.append(sorted(actual))
    return filas


def columnas(frags):
    """Dónde empieza cada columna de la tabla, según dónde se alinean las siglas de bancada (FP, JP...)."""
    xs = sorted(x for x, y, t in frags if t.strip().rstrip(".") in SIGLAS)
    grupos = []
    for x in xs:
        if grupos and x - grupos[-1][-1] < 40:
            grupos[-1].append(x)
        else:
            grupos.append([x])
    inicios = sorted(min(g) for g in grupos if len(g) >= 5)
    return [i - 8 for i in inicios]


def leer_registro(toks, lista, ocr):
    """Una celda de la tabla: [n°] [bancada] apellidos, nombres estado -> registro o None."""
    t = [x for x in toks if not re.fullmatch(r"[-–—_.]+", x)]
    if t and re.fullmatch(r"\d{1,3}\.?", t[0]):  # plantilla numerada
        t = t[1:]
    if t and t[0].rstrip(".") in SIGLAS:
        t = t[1:]
    if len(t) < 2:
        return None
    est, conf = estado_de(t[-1], ocr)
    if est:
        d, sc = casar(" ".join(t[:-1]), lista)
        if d:
            return {"congresista": d["nombre"], "bancada": d["bancada"], "codigo": est, "dudoso": conf < 0.95 or sc < 0.9}
    # estado pegado al nombre («ALEJANDROPRE», «YENIFERSI»)
    for cod in sorted((c for c in ESTADOS if len(c) >= 2), key=len, reverse=True):
        if t[-1].upper().endswith(cod.upper()) and len(t[-1]) >= len(cod) + 3:
            d, sc = casar(" ".join(t[:-1] + [t[-1][: -len(cod)]]), lista)
            if d and sc >= 0.9:
                return {"congresista": d["nombre"], "bancada": d["bancada"], "codigo": cod, "dudoso": True}
    return None


def cuadro_bancadas(lineas_tok):
    """Votos por bancada impresos: «FP FUERZA POPULAR 30 0 0 0» -> {FP: [si, no, abst, sin_resp]}."""
    out = {}
    for toks in lineas_tok:
        for i, tok in enumerate(toks):
            sig = "OBRAS" if tok.rstrip(".") == "PCO" else tok.rstrip(".")
            if sig in BANCADAS and i + 1 < len(toks) and clave("".join(toks[i + 1:i + 6])).startswith(BANCADAS[sig][:8]):
                nums = [int(x) for x in toks[i + 1:] if re.fullmatch(r"\d{1,3}", x)]
                if len(nums) >= 4:
                    out[sig] = nums[:4]
    return out


def leer_pagina(frags, texto, lista, ocr) -> dict:
    lineas = filas_por_y(frags)
    lineas_tok = [" ".join(t for _, _, t in fila).split() for fila in lineas]
    compacto = clave(texto) if texto else clave(" ".join(" ".join(l) for l in lineas_tok))
    tipo = "Votación" if "VOTACION" in compacto[:400] and "ASUNTO" in compacto[:600] else \
        ("Asistencia" if "ASISTENCIA" in compacto[:400] and "FECHA" in compacto[:500] else "")

    plano = " ".join(" ".join(l) for l in lineas_tok)
    fecha = re.search(r"Fecha\s*:?\s*(\d{2})/(\d{2})/(\d{4})", plano)
    hora = re.search(r"Hora\s*:?\s*(\d{1,2}:\d{2})\s*([AP]M)", plano, re.I)

    totales = {}
    for toks in lineas_tok:
        comp = "".join(toks).upper().replace(" ", "")
        comp = unicodedata.normalize("NFKD", comp).encode("ascii", "ignore").decode()
        for patron, k in TOTALES:
            m = re.match(patron, comp)
            if m and k not in totales:
                totales[k] = int(m.group(1))

    entradas, vistos = [], set()
    if tipo:
        cortes = columnas(frags)
        if cortes:
            limites = cortes[1:] + [10_000]
            for i, ini in enumerate(cortes):
                celdas = [f for f in frags if ini <= f[0] < limites[i]]
                for fila in filas_por_y(celdas):
                    reg = leer_registro(" ".join(t for _, _, t in fila).split(), lista, ocr)
                    if reg and reg["congresista"] not in vistos:
                        vistos.add(reg["congresista"])
                        entradas.append(reg)
        pres = re.search(r"Presidenta?\s*:\s*([^\n]+?)(?:\s+Sesi[oó]n|\s+CÁMARA|$)", plano)
        if pres:
            d, sc = casar(pres.group(1), lista)
            if d and d["nombre"] not in vistos:
                vistos.add(d["nombre"])
                entradas.append({"congresista": d["nombre"], "bancada": d["bancada"], "codigo": "***", "dudoso": False})

    asunto = ""
    if tipo == "Votación":
        m = re.search(r"Asunto\s*:?\s*(.*?)\s+(?:FP|JP|PBG|PCO|RP|AN|OBRAS|1)\s+[A-ZÁÉÍÓÚÑ]{3}", plano)
        asunto = m.group(1).strip() if m else ""

    # constancia de voto oral: el presidente deja constancia del voto de quienes el sistema no registró
    orales = []
    m = re.search(r"deja\s+constancia\s+del?\s+voto\s+(a\s+favor|en\s+contra)\s+de\s+(?:l|los|las|la)?\s*"
                  r"(?:diputad[oa]s?|senador(?:a|es|as)?|congresistas?)\s+([^.*]+)", plano, re.I)
    if m and entradas:
        voto = "SI" if "favor" in m.group(1).lower() else "NO"
        for apellido in re.split(r",|\s+y\s+", m.group(2)):
            cands = [e for e in entradas if clave(e["congresista"]).startswith(clave(apellido))] if len(clave(apellido)) >= 5 else []
            if len(cands) == 1:
                cands[0]["codigo_original"], cands[0]["codigo"], cands[0]["oral"] = cands[0]["codigo"], voto, True
                orales.append(cands[0]["congresista"])

    nota = {}
    if not tipo:  # acta sin tabla: se rescata el resultado del texto
        tipo = "Nota"
        t = re.sub(r"\s+", " ", texto or plano)
        a = re.search(r"(\d+)\s*votos?\s*a\s*favor", t, re.I)
        c = re.search(r"(\d+)\s*(?:votos?)?\s*en\s*contra", t, re.I)
        b = re.search(r"(\d+)\s*abstenci", t, re.I)
        totales.update({k: int(x.group(1)) for k, x in (("a_favor", a), ("en_contra", c), ("abstencion", b)) if x})
        nota["texto"] = t[:600]
        aprob = re.search(r"(no\s+(?:fue\s+)?aprob|rechaz|se\s+aprob|fue\s+aprobad|aprob[oó])", t, re.I)
        nota["resultado"] = ("No aprobado" if aprob and re.match(r"no|rechaz", aprob.group(1), re.I) else
                             "Aprobado" if aprob else "")
    return {"tipo": tipo, "fecha": f"{fecha.group(3)}-{fecha.group(2)}-{fecha.group(1)}" if fecha else "",
            "hora": f"{hora.group(1)} {hora.group(2).upper()}" if hora else "", "asunto": asunto,
            "entradas": entradas, "totales": totales, "bancadas": cuadro_bancadas(lineas_tok) if tipo == "Votación" else {},
            "orales": orales, **nota}


# ===================== Texto u OCR =====================
_motor = []


def frags_ocr(pdf: Path, i: int, cache: dict, ruta_cache: Path):
    if str(i) not in cache:
        import numpy as np
        import pypdfium2 as pdfium
        from rapidocr_onnxruntime import RapidOCR
        if not _motor:  # parámetros más sensibles que los de fábrica: recuperan más estados en los escaneos
            _motor.append(RapidOCR(box_thresh=0.3, unclip_ratio=2.0, text_score=0.3))
        img = pdfium.PdfDocument(str(pdf))[i].render(scale=ESCALA_OCR).to_pil().convert("RGB")
        res, _ = _motor[0](np.array(img))
        cache[str(i)] = [[min(p[0] for p in b) / ESCALA_OCR, sum(p[1] for p in b) / 4 / ESCALA_OCR, t]
                         for b, t, c in (res or [])]
        ruta_cache.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    return [tuple(f) for f in cache[str(i)]]


def leer_pdf(pdf: Path, camara: str, maestro: dict, usar_ocr: bool, forzar: bool) -> list:
    h = sha(pdf)
    ruta_lect = DIR_CACHE / f"lectura_{h}.json"
    if ruta_lect.exists() and not forzar:
        c = json.loads(ruta_lect.read_text(encoding="utf-8"))
        if c["version"] == VERSION_LECTOR and not c["pendiente_ocr"]:
            return c["paginas"]
    ruta_ocr = DIR_CACHE / f"ocr_{h}.json"
    cache_ocr = json.loads(ruta_ocr.read_text(encoding="utf-8")) if ruta_ocr.exists() else {}
    paginas, pendiente = [], False
    with pdfplumber.open(pdf) as doc:
        for i, pg in enumerate(doc.pages):
            texto = pg.extract_text() or ""
            if len(texto.strip()) > 50:
                frags = [(w["x0"], (w["top"] + w["bottom"]) / 2, w["text"]) for w in pg.extract_words()]
                fuente = "texto"
            elif usar_ocr:
                frags, texto, fuente = frags_ocr(pdf, i, cache_ocr, ruta_ocr), "", "OCR"
            else:
                pendiente = True
                continue
            p = leer_pagina(frags, texto, maestro[camara], fuente == "OCR")
            p.update(pagina=i + 1, fuente=fuente)
            if fuente == "texto" and usar_ocr and p["tipo"] != "Nota" and control(p) != "OK":
                # a veces el Congreso deja algunas filas solo como imagen: el OCR completa a quienes falten
                extra = leer_pagina(frags_ocr(pdf, i, cache_ocr, ruta_ocr), "", maestro[camara], True)
                ya = {e["congresista"] for e in p["entradas"]}
                nuevos = [dict(e, dudoso=True) for e in extra["entradas"] if e["congresista"] not in ya]
                if nuevos:
                    p["entradas"] += nuevos
                    p["fuente"] = "texto+OCR"
            paginas.append(p)
    ruta_lect.write_text(json.dumps({"version": VERSION_LECTOR, "pendiente_ocr": pendiente, "paginas": paginas},
                                    ensure_ascii=False), encoding="utf-8")
    return paginas


# ===================== Control y salida =====================
def control(p: dict) -> str:
    """Compara lo leído con los totales impresos. OK si cuadran; si no, dice qué revisar."""
    if p["tipo"] == "Nota":
        return "Nota (sin tabla nominal)"
    cod = [e["codigo"] for e in p["entradas"]]
    pares = [("presentes", "PRE"), ("ausentes", "AUS")] if p["tipo"] == "Asistencia" else \
        [("a_favor", "SI"), ("en_contra", "NO"), ("abstencion", "Abst.")]
    dif = [f"{k}: leídos {cod.count(c)} vs impresos {p['totales'][k]}" for k, c in pares
           if k in p["totales"] and cod.count(c) != p["totales"][k]]
    if not p["totales"]:
        dif.append("sin totales impresos legibles")
    return "OK" if not dif else "REVISAR: " + "; ".join(dif)


def resultado(detalle: str, p: dict) -> str:
    """El movimiento del expediente dice el resultado oficial («... (NO APROBADO)»); si no lo dice, los totales."""
    d = detalle.upper()
    if re.search(r"NO APROBAD|RECHAZAD", d):
        return "No aprobado"
    if "APROBAD" in d:
        return "Aprobado"
    t = p["totales"]
    if "a_favor" in t and "en_contra" in t:
        return "Aprobado" if t["a_favor"] > t["en_contra"] else "No aprobado"
    return p.get("resultado", "")


def votaciones_de_expedientes() -> dict:
    """{url_pdf: {"camara", "fecha", "detalle", "proposiciones": [...]}} desde los movimientos de votación."""
    pdfs = {}
    with open(MOVIMIENTOS, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if not r["seg_detalle"].upper().startswith("ASISTENCIA Y VOTACI"):
                continue
            for url in filter(None, r["seg_adjuntos"].split(" | ")):
                d = pdfs.setdefault(url, {"camara": r["camara"], "fecha": r["seg_fecha"],
                                          "detalle": r["seg_detalle"].split(" - ", 1)[-1].strip(), "proposiciones": []})
                if r["pl_id"] not in d["proposiciones"]:
                    d["proposiciones"].append(r["pl_id"])
    return pdfs


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description="Votaciones del Pleno vinculadas a los proyectos de ley")
    ap.add_argument("--sin-ocr", action="store_true", help="no lee las páginas escaneadas")
    ap.add_argument("--forzar", action="store_true", help="vuelve a leer todo (el OCR en caché se conserva)")
    ap.add_argument("--solo", default=None, help="solo el PDF cuyo id contenga este texto")
    a = ap.parse_args()

    DIR_PDF.mkdir(parents=True, exist_ok=True)
    DIR_CACHE.mkdir(parents=True, exist_ok=True)
    maestro = cargar_maestro()
    pdfs = votaciones_de_expedientes()
    print(f"{len(pdfs)} PDF de votación en {len({p for d in pdfs.values() for p in d['proposiciones']})} proposiciones")

    sesion, votos, resumen = requests.Session(), [], []
    for url, meta in pdfs.items():
        id_pdf = url.rstrip("/").split("/")[-2]
        if a.solo and a.solo not in id_pdf:
            continue
        ruta = DIR_PDF / f"{id_pdf}.pdf"
        if not ruta.exists():
            r = sesion.get(url, headers=HEADERS, timeout=60)
            r.raise_for_status()
            ruta.write_bytes(r.content)
        paginas = leer_pdf(ruta, meta["camara"], maestro, not a.sin_ocr, a.forzar)
        for p in paginas:
            ctrl = control(p)
            base = {"camara": meta["camara"], "proposiciones": "; ".join(meta["proposiciones"]), "pdf": id_pdf,
                    "pagina": p["pagina"], "fecha": p["fecha"] or meta["fecha"], "tipo": p["tipo"]}
            t = p["totales"]
            resumen.append({**base, "hora": p["hora"], "movimiento": meta["detalle"],
                            "asunto": p["asunto"] or meta["detalle"],
                            "resultado": resultado(meta["detalle"], p) if p["tipo"] != "Asistencia" else "",
                            "a_favor": t.get("a_favor", ""), "en_contra": t.get("en_contra", ""),
                            "abstencion": t.get("abstencion", ""), "sin_respuesta": t.get("sin_respuesta", ""),
                            "presentes": t.get("presentes", ""), "ausentes": t.get("ausentes", ""),
                            "votos_por_bancada": json.dumps(p["bancadas"], ensure_ascii=False) if p["bancadas"] else "",
                            "leidos": len(p["entradas"]), "orales": "; ".join(p["orales"]),
                            "fuente": p["fuente"], "control": ctrl, "url": url})
            for e in p["entradas"]:
                votos.append({**base, "congresista": e["congresista"], "bancada": e["bancada"],
                              "codigo": e["codigo"], "resultado": ESTADOS.get(e["codigo"], e["codigo"]),
                              "voto_oral": "sí" if e.get("oral") else "", "fuente": p["fuente"],
                              "revisar": "sí" if e["dudoso"] or ctrl != "OK" else ""})
            print(f"  {id_pdf} p{p['pagina']} {p['tipo']:10} {p['fuente']:5} leídos {len(p['entradas']):3} | {ctrl}")

    for nombre, filas in (("votos.csv", votos), ("votaciones.csv", resumen)):
        if filas:
            with open(DATA / nombre, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=list(filas[0]))
                w.writeheader()
                w.writerows(filas)
    ok = sum(r["control"] == "OK" for r in resumen)
    print(f"\nListo: {len(resumen)} páginas ({ok} cuadran con los totales impresos), {len(votos)} votos individuales")


if __name__ == "__main__":
    main()
