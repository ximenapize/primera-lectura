# pdf_texto.py
# Descarga el PDF de una proposición, extrae su texto y separa las dos partes que importan:
#   - la fórmula legal (el articulado: lo que de verdad cambiaría la ley)
#   - el inicio de la exposición de motivos (la justificación)
# El texto completo se guarda en data/textos/ (ignorado por git) para no descargar dos veces.
import io
import re
import unicodedata
from pathlib import Path

import requests
from pypdf import PdfReader

RAIZ = Path(__file__).resolve().parents[1]
CACHE = RAIZ / "data" / "textos"
HEADERS = {"User-Agent": "Mozilla/5.0 (scrapeo academico)"}


def texto_pdf(url: str, clave: str) -> str:
    CACHE.mkdir(parents=True, exist_ok=True)
    ruta = CACHE / f"{clave}.txt"
    if ruta.exists():
        return ruta.read_text(encoding="utf-8")
    r = requests.get(url, headers=HEADERS, timeout=120)
    r.raise_for_status()
    paginas = [p.extract_text() or "" for p in PdfReader(io.BytesIO(r.content)).pages]
    texto = "\n".join(paginas)
    ruta.write_text(texto, encoding="utf-8")
    return texto


def normalizar(s: str) -> str:
    """Minúsculas, sin tildes y con espacios simples: para buscar citas aunque el PDF venga desordenado."""
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return " ".join(re.sub(r"[^a-z0-9 ]", " ", s).split())


def partes(texto: str, max_formula: int = 6000, max_motivos: int = 2000) -> dict:
    t = re.sub(r"[ \t]+", " ", texto)
    m = re.search(r"F[ÓO]RMULA\s+LEGAL", t, re.I) or re.search(r"Art[íi]culo\s+(1|[úu]nico)\b", t, re.I)
    inicio = m.start() if m else 0
    formula = t[inicio:inicio + max_formula]

    e = re.search(r"EXPOSICI[ÓO]N\s+DE\s+MOTIVOS", t, re.I)
    motivos = t[e.end():e.end() + max_motivos] if e else ""
    legible = sum(c.isalpha() for c in t[:5000]) / max(len(t[:5000]), 1)
    return {"formula": formula.strip(), "motivos": motivos.strip(), "legible": round(legible, 2), "chars": len(t)}


def cita_verificada(cita: str, texto: str) -> bool:
    """¿La cita que dio el modelo aparece en el PDF? Basta que coincida un tramo de 8 palabras seguidas."""
    c, t = normalizar(cita).split(), normalizar(texto)
    if len(c) < 4:
        return False
    if len(c) <= 8:
        return " ".join(c) in t
    return any(" ".join(c[i:i + 8]) in t for i in range(len(c) - 7))
