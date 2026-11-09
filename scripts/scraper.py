# scraper.py
# Descarga las proposiciones legislativas de las DOS cámaras (Diputados y Senado) desde la API del portal
# del Congreso y deja dos archivos:
#   data/movimientos.csv    una fila por movimiento del seguimiento (presentado, en comisión, dictamen...)
#   data/proposiciones.csv  una fila por proposición, con su estado actual y el PDF del proyecto
# Uso: uv run scripts/scraper.py            (opciones: --periodo, --camaras, --limite, --pausa, --salida)
# Basado en 01_generar_base_csv.py (un scraper por cámara); aquí se unifican en una sola corrida.
import argparse, base64, csv, re, sys, time
from pathlib import Path
from typing import Dict, List, Optional

import requests
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

# ===================== Config =====================
API = "https://api.congreso.gob.pe/spley-portal-service"
PORTAL = "https://wb2server.congreso.gob.pe/spley-portal/#/{ruta}/expediente/{anio}/{numero}"
CAMARAS = {"D": "diputados", "S": "senado"}
# Clave pública embebida en el JavaScript del portal: la usa el propio navegador para cifrar los ids de la URL.
AES_KEY = b"ProdALg5ZrAsxBMD"
HEADERS = {"User-Agent": "Mozilla/5.0 (scrapeo academico)", "Accept": "application/json"}

META = [
    "camara", "pl_id", "url", "periodo", "legislatura", "fecha_presentacion", "proponente",
    "titulo", "sumilla", "autor_principal", "coautores", "adherentes", "grupo_parlamentario",
    "comisiones", "ultimo_estado",
]
COL_MOVIMIENTOS = META + ["seg_fecha", "seg_estado", "seg_comision", "seg_detalle", "seg_adjuntos"]
COL_PROPOSICIONES = META + ["n_movimientos", "fecha_ultimo_movimiento", "pdf_proyecto", "adjuntos"]


# ===================== API =====================
def enc(valor) -> str:
    c = AES.new(AES_KEY, AES.MODE_ECB).encrypt(pad(str(valor).encode(), 16))
    return base64.b64encode(c).decode().replace("+", "-").replace("/", "_").replace("=", "")


def pedir(sesion: requests.Session, metodo: str, url: str, reintentos: int = 4, **kw) -> dict:
    for intento in range(1, reintentos + 1):
        try:
            r = sesion.request(metodo, url, timeout=60, **kw)
            if r.status_code == 200:
                return r.json()
            if r.status_code in (429, 500, 502, 503, 504):
                raise requests.HTTPError(f"HTTP {r.status_code}")
            r.raise_for_status()
        except (requests.RequestException, ValueError) as e:
            if intento == reintentos:
                raise
            espera = 2 ** intento
            print(f"  [reintento {intento}/{reintentos - 1} en {espera}s] {e}")
            time.sleep(espera)


def listar(sesion, periodo: int, tipo: str, pagina: int = 500) -> List[dict]:
    proyectos: List[dict] = []
    total = None
    while total is None or len(proyectos) < total:
        cuerpo = {
            "perParId": periodo, "codTipoParl": tipo, "perLegId": None, "comisionId": None, "estadoId": None,
            "congresistaId": None, "grupoParlamentarioId": None, "proponenteId": None, "legislaturaId": None,
            "fecPresentacionDesde": None, "fecPresentacionHasta": None, "pleyNum": None, "palabras": None,
            "tipoFirmanteId": None, "pageSize": pagina, "rowStart": len(proyectos),
        }
        data = pedir(sesion, "POST", f"{API}/proyecto-ley/lista-con-filtro", json=cuerpo)["data"]
        if not data["proyectos"]:
            break
        total = data["rowsTotal"]
        proyectos += data["proyectos"]
    if total is not None and len(proyectos) != total:
        raise RuntimeError(f"La lista trajo {len(proyectos)} de {total} proyectos")
    return sorted(proyectos, key=lambda p: p["pleyNum"])


def catalogo_comisiones(sesion, periodo: int, tipo: str) -> Dict[int, str]:
    f = pedir(sesion, "GET", f"{API}/periodo-parlamentario/{periodo}/filtros", params={"codTipoParl": tipo})["data"]
    return {c["id"]: limpiar(c["descripcion"]) for c in f["comisiones"]}


def detalle(sesion, periodo: int, numero: int, tipo: str) -> dict:
    return pedir(sesion, "GET", f"{API}/expediente/{enc(periodo)}/{enc(numero)}", params={"codTipoParl": tipo})["data"]


# ===================== Transformación =====================
def limpiar(s: Optional[str]) -> str:
    return " ".join(str(s).split()) if s else ""


def enlace_adjunto(a: dict) -> str:
    if a.get("enlace"):
        return a["enlace"]
    return f"{API}/archivo/{base64.b64encode(str(a['proyectoArchivoId']).encode()).decode()}/pdf"


def comisiones_seg(s: dict, catalogo: Dict[int, str]) -> List[str]:
    """Nombres de comisión de un movimiento. Varios nombres llevan coma, así que se resuelven por id."""
    ids = [int(i) for i in re.findall(r"\d+", str(s.get("idsComisiones") or ""))]
    nombres = [catalogo.get(i) for i in ids]
    if ids and all(nombres):
        return nombres
    texto = limpiar(s.get("desComisiones"))
    return [texto] if texto else []


def filas_planas(d: dict, tipo: str, catalogo: Dict[int, str]) -> List[dict]:
    g = d["general"]
    codigo = g["proyectoLey"]
    numero = int(codigo.split("-")[0])

    # el API entrega el seguimiento del más reciente al más antiguo
    segs = sorted(d["seguimientos"], key=lambda s: (s["fecha"], s.get("seguimientoPleyId") or 0))

    comisiones: List[str] = []
    for s in segs:
        for c in comisiones_seg(s, catalogo):
            if c not in comisiones:
                comisiones.append(c)

    por_tipo: Dict[int, List[str]] = {1: [], 2: [], 3: []}  # 1=Autor principal, 2=Coautor, 3=Adherente
    for f in d["firmantes"]:
        por_tipo.setdefault(f["tipoFirmanteId"], []).append(limpiar(f["nombre"]))

    meta = {
        "camara": CAMARAS[tipo], "pl_id": codigo,
        "url": PORTAL.format(ruta=CAMARAS[tipo], anio=g["perParId"], numero=numero),
        "periodo": g["desPerParAbrev"], "legislatura": limpiar(g["desLegis"]),
        "fecha_presentacion": g["fecPresentacion"], "proponente": limpiar(g["desProponente"]),
        "titulo": limpiar(g["titulo"]), "sumilla": limpiar(g["sumilla"]),
        "autor_principal": ", ".join(por_tipo.get(1, [])), "coautores": "; ".join(por_tipo.get(2, [])),
        "adherentes": "; ".join(por_tipo.get(3, [])), "grupo_parlamentario": limpiar(g["desGpar"]),
        "comisiones": "; ".join(comisiones), "ultimo_estado": limpiar(g["desEstado"]),
    }
    filas = [{
        **meta,
        "seg_fecha": s["fecha"][:10],
        "seg_estado": limpiar(s["desEstado"]),
        "seg_comision": "; ".join(comisiones_seg(s, catalogo)),
        "seg_detalle": limpiar(s.get("detalle")),
        "seg_adjuntos": " | ".join(enlace_adjunto(a) for a in s.get("archivos") or []),
    } for s in segs]
    # expediente sin seguimiento: se conserva igual
    return filas or [{**meta, "seg_fecha": "", "seg_estado": "", "seg_comision": "", "seg_detalle": "", "seg_adjuntos": ""}]


def resumir(filas: List[dict]) -> dict:
    """Una fila por proposición. El PDF del proyecto es el primer PDF del portal en el movimiento más antiguo."""
    adjuntos = [u for f in filas for u in f["seg_adjuntos"].split(" | ") if u]
    pdfs = [u for u in adjuntos if u.startswith(API)]
    return {
        **{k: filas[0][k] for k in META},
        "n_movimientos": sum(1 for f in filas if f["seg_fecha"]),
        "fecha_ultimo_movimiento": max((f["seg_fecha"] for f in filas), default=""),
        "pdf_proyecto": pdfs[0] if pdfs else "",
        "adjuntos": " | ".join(dict.fromkeys(adjuntos)),
    }


def escribir(ruta: Path, columnas: List[str], filas: List[dict]) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    tmp = ruta.with_suffix(".tmp")
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=columnas)
        w.writeheader()
        w.writerows(filas)
    tmp.replace(ruta)  # se reemplaza de un golpe: nunca queda un CSV a medias


# ===================== Main =====================
def scrapear_camara(sesion, periodo: int, tipo: str, limite: Optional[int], pausa: float) -> List[List[dict]]:
    lista = listar(sesion, periodo, tipo)
    catalogo = catalogo_comisiones(sesion, periodo, tipo)
    print(f"{CAMARAS[tipo]}: {len(lista)} proposiciones")
    if limite:
        lista = lista[:limite]

    resultados: Dict[int, List[dict]] = {}
    pendientes = [item["pleyNum"] for item in lista]
    for ronda in (1, 2):  # segunda ronda solo para los que fallaron
        fallidos = []
        for i, n in enumerate(pendientes, 1):
            try:
                resultados[n] = filas_planas(detalle(sesion, periodo, n, tipo), tipo, catalogo)
                print(f"  [{CAMARAS[tipo]} {i}/{len(pendientes)}] {resultados[n][0]['pl_id']}")
            except Exception as e:
                fallidos.append(n)
                print(f"  [{CAMARAS[tipo]} {i}/{len(pendientes)}] ERROR n={n}: {e}")
            time.sleep(pausa)
        if not fallidos:
            break
        pendientes = fallidos
        print(f"  Reintentando {len(fallidos)} expedientes...")
    if fallidos:
        sys.exit(f"{CAMARAS[tipo]}: fallaron {len(fallidos)} expedientes {fallidos}. No se escribió nada.")
    return [resultados[n] for n in sorted(resultados)]


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(description="Proposiciones legislativas de Diputados y Senado en una sola base")
    p.add_argument("--periodo", type=int, default=2026, help="perParId, p. ej. 2026 (= 2026-2031)")
    p.add_argument("--camaras", default="DS", help="D = Diputados, S = Senado (por defecto ambas)")
    p.add_argument("--salida", default="data", help="carpeta de salida")
    p.add_argument("--pausa", type=float, default=0.4, help="segundos entre peticiones de detalle")
    p.add_argument("--limite", type=int, default=None, help="solo los primeros N por cámara (para pruebas)")
    a = p.parse_args()

    sesion = requests.Session()
    sesion.headers.update(HEADERS)

    por_proposicion: List[List[dict]] = []
    for tipo in a.camaras.upper():
        por_proposicion += scrapear_camara(sesion, a.periodo, tipo, a.limite, a.pausa)

    movimientos = [f for filas in por_proposicion for f in filas]
    proposiciones = sorted((resumir(filas) for filas in por_proposicion),
                           key=lambda r: (r["fecha_presentacion"], r["camara"], r["pl_id"]), reverse=True)

    salida = Path(a.salida)
    escribir(salida / "movimientos.csv", COL_MOVIMIENTOS, movimientos)
    escribir(salida / "proposiciones.csv", COL_PROPOSICIONES, proposiciones)
    print(f"\nListo: {len(proposiciones)} proposiciones, {len(movimientos)} movimientos en {salida}/")


if __name__ == "__main__":
    main()
