# pdf_texto.py
# Descarga el PDF de una proposición, extrae su texto y separa las dos partes que importan:
#   - la fórmula legal (el articulado: lo que de verdad cambiaría la ley)
#   - el inicio de la exposición de motivos (la justificación)
# El texto completo se guarda en data/textos/ (ignorado por git) para no descargar dos veces.
# Si una página no tiene texto extraíble (PDF escaneado), se lee con OCR.
import io
import re
import unicodedata
from pathlib import Path

import requests
from pypdf import PdfReader

RAIZ = Path(__file__).resolve().parents[1]
CACHE = RAIZ / "data" / "textos"
HEADERS = {"User-Agent": "Mozilla/5.0 (scrapeo academico)"}


MAX_PAGINAS_OCR = 6  # oficio + fórmula legal caben en las primeras páginas; cada página con OCR tarda ~15-20 s
_motor = []


def pobre(texto: str) -> bool:
    """Página o documento sin texto que sirva: casi vacío o con pocas letras (un escaneo, una firma, un sello)."""
    t = texto.strip()
    return len(t) < 200 or sum(c.isalpha() for c in t[:3000]) / max(len(t[:3000]), 1) < 0.4


def ocr_pagina(pdf_bytes: bytes, i: int) -> str:
    """Lee una página escaneada con OCR (RapidOCR, el mismo de las votaciones) y la devuelve en orden de lectura."""
    import numpy as np
    import pypdfium2 as pdfium
    from rapidocr_onnxruntime import RapidOCR
    if not _motor:
        _motor.append(RapidOCR())
    img = pdfium.PdfDocument(pdf_bytes)[i].render(scale=2).to_pil().convert("RGB")
    res, _ = _motor[0](np.array(img))
    # cada caja: (esquinas, texto, confianza); se ordenan por renglón (y) y luego de izquierda a derecha (x)
    cajas = sorted(((round(b[0][1] / 25), b[0][0], t) for b, t, _c in (res or [])))
    lineas, actual, fila = [], [], None
    for y, _x, t in cajas:
        if fila is not None and y != fila:
            lineas.append(" ".join(actual)); actual = []
        actual.append(t); fila = y
    if actual:
        lineas.append(" ".join(actual))
    return "\n".join(lineas)


def texto_pdf(url: str, clave: str, ocr: bool = True) -> str:
    """Texto del PDF. Las páginas sin texto extraíble (escaneadas) se leen con OCR.
    Cache: data/textos/<clave>.txt (texto nativo) y <clave>.ocr.txt (con OCR, cuando hizo falta)."""
    CACHE.mkdir(parents=True, exist_ok=True)
    ruta, ruta_ocr = CACHE / f"{clave}.txt", CACHE / f"{clave}.ocr.txt"
    if ruta_ocr.exists():
        return ruta_ocr.read_text(encoding="utf-8")
    if ruta.exists() and (not ocr or not pobre(ruta.read_text(encoding="utf-8"))):
        return ruta.read_text(encoding="utf-8")
    r = requests.get(url, headers=HEADERS, timeout=120)
    r.raise_for_status()
    paginas = [p.extract_text() or "" for p in PdfReader(io.BytesIO(r.content)).pages]
    ruta.write_text("\n".join(paginas), encoding="utf-8")  # reemplaza un cache vacío de una descarga fallida
    if not ocr or not any(pobre(p) for p in paginas[:MAX_PAGINAS_OCR]):
        return "\n".join(paginas)
    paginas = [ocr_pagina(r.content, i) if i < MAX_PAGINAS_OCR and pobre(p) else p for i, p in enumerate(paginas)]
    texto = "\n".join(paginas)
    ruta_ocr.write_text(texto, encoding="utf-8")
    return texto


def normalizar(s: str) -> str:
    """Minúsculas, sin tildes y con espacios simples: para buscar citas aunque el PDF venga desordenado."""
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return " ".join(re.sub(r"[^a-z0-9 ]", " ", s).split())


def partes(texto: str, max_formula: int = 6000, max_motivos: int = 2000) -> dict:
    t = re.sub(r"[ \t]+", " ", texto)
    # \s* y no \s+: el OCR a veces pega las palabras ("FORMULALEGAL", "Articulo1")
    m = re.search(r"F[ÓO]RMULA\s*LEGAL", t, re.I) or re.search(r"Art[íi]culo\s*(1|[úu]nico)\b", t, re.I)
    inicio = m.start() if m else 0
    formula = t[inicio:inicio + max_formula]

    e = re.search(r"EXPOSICI[ÓO]N\s*DE\s*MOTIVOS", t, re.I)
    motivos = t[e.end():e.end() + max_motivos] if e else ""
    legible = sum(c.isalpha() for c in t[:5000]) / max(len(t[:5000]), 1)
    return {"formula": formula.strip(), "motivos": motivos.strip(), "legible": round(legible, 2), "chars": len(t)}


def cita_verificada(cita: str, texto: str) -> bool:
    """¿La cita que dio el modelo aparece en el PDF? Basta que coincida un tramo de 8 palabras seguidas."""
    c, t = normalizar(cita).split(), normalizar(texto)
    if len(c) < 4:
        return False
    if len(c) <= 8:
        return " ".join(c) in t or "".join(c) in t.replace(" ", "")
    if any(" ".join(c[i:i + 8]) in t for i in range(len(c) - 7)):
        return True
    # texto de OCR con palabras pegadas: se compara sin espacios
    pegado = t.replace(" ", "")
    return any("".join(c[i:i + 8]) in pegado for i in range(len(c) - 7))
