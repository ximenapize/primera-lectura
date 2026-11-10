# maestro.py
# Base aparte de congresistas 2026-2031 (Diputados y Senado): nombre oficial, bancada y cámara.
# La usan el lector de votaciones (para reconocer nombres cortados o mal leídos por OCR) y la app.
# Fuente: la API de WordPress de cada cámara. Si falla, se conserva el maestro que ya existe.
# Salida: data/maestro_congresistas.csv
# Uso: uv run scripts/maestro.py
import csv
import re
import sys
import unicodedata
from pathlib import Path

import requests

RAIZ = Path(__file__).resolve().parents[1]
SALIDA = RAIZ / "data" / "maestro_congresistas.csv"
HEADERS = {"User-Agent": "Mozilla/5.0 (scrapeo academico)"}
ENDPOINTS = {
    "diputados": "https://diputados.congreso.gob.pe/wp-json/wp/v2/diputado",
    "senado": "https://senado.congreso.gob.pe/wp-json/wp/v2/senador",
}
# slug de WordPress -> (sigla de los PDF de votación, nombre como en el portal de proposiciones)
BANCADAS = {
    "ahora-nacion": ("AN", "Ahora Nación"),
    "fuerza-popular": ("FP", "Fuerza Popular"),
    "juntos-por-el-peru": ("JP", "Juntos por el Perú"),
    "partido-civico-obras": ("OBRAS", "Partido Cívico Obras"),
    "partido-del-buen-gobierno": ("PBG", "Partido del Buen Gobierno"),
    "renovacion-popular": ("RP", "Renovación Popular"),
}
SIGLA_A_NOMBRE = {s: n for s, n in BANCADAS.values()}
COLUMNAS = ["congresista", "bancada", "bancada_nombre", "camara", "clave"]


def clave(s: str) -> str:
    """Nombre reducido a letras A-Z sin tildes ni espacios: para comparar nombres leídos de PDF u OCR."""
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().upper()
    return re.sub(r"[^A-Z]", "", s)


def descargar_camara(camara: str, url: str) -> list:
    filas, pagina = [], 1
    while True:
        r = requests.get(url, params={"per_page": 100, "page": pagina}, headers=HEADERS, timeout=30)
        if r.status_code == 400 and pagina > 1:  # WordPress responde 400 al pasar la última página
            break
        r.raise_for_status()
        for item in r.json():
            nombre = " ".join(item["title"]["rendered"].split())
            slugs = [c.removeprefix("grupo_parlamentario-") for c in item.get("class_list", [])
                     if c.startswith("grupo_parlamentario-")]
            if not slugs or slugs[0] not in BANCADAS:
                raise RuntimeError(f"Bancada desconocida para {nombre} ({camara}): {slugs}. Actualiza BANCADAS.")
            sigla, nombre_bancada = BANCADAS[slugs[0]]
            filas.append({"congresista": nombre, "bancada": sigla, "bancada_nombre": nombre_bancada,
                          "camara": camara, "clave": clave(nombre)})
        if pagina >= int(r.headers.get("X-WP-TotalPages", "1")):
            break
        pagina += 1
    return filas


def cargar() -> list:
    with open(SALIDA, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main():
    try:
        filas = [f for camara, url in ENDPOINTS.items() for f in descargar_camara(camara, url)]
    except Exception as e:
        if SALIDA.exists():
            sys.exit(f"No se pudo actualizar el maestro ({e}); se conserva {SALIDA.name}.")
        raise
    n = {c: sum(f["camara"] == c for f in filas) for c in ENDPOINTS}
    if n["diputados"] < 120 or n["senado"] < 55:  # 130 diputados y 60 senadores: si faltan muchos, algo cambió
        sys.exit(f"El maestro salió incompleto {n}; no se sobrescribe.")
    SALIDA.parent.mkdir(exist_ok=True)
    with open(SALIDA, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNAS)
        w.writeheader()
        w.writerows(sorted(filas, key=lambda f: (f["camara"], f["congresista"])))
    print(f"Maestro: {n['diputados']} diputados, {n['senado']} senadores -> {SALIDA}")


if __name__ == "__main__":
    main()
