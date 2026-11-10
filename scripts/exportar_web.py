# exportar_web.py
# Convierte las bases de data/ en los JSON que lee el sitio estático (site/, publicado en GitHub Pages).
# Junta cada proposición con su temática, su lectura de riesgo (la revisión del agente reemplaza a la del modelo
# local), su recorrido y sus votaciones. Uso: uv run scripts/exportar_web.py
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ai"))
from preguntas import PREGUNTAS  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
DATA = RAIZ / "data"
SALIDA = RAIZ / "site" / "data"


def leer_jsonl(ruta: Path) -> list:
    return [json.loads(l) for l in ruta.read_text(encoding="utf-8").splitlines() if l] if ruta.exists() else []


def estado_simple(e: str) -> int:
    """Avance en 5 pasos: 0 archivado, 1 presentado, 2 comisión, 3 dictamen, 4 Pleno, 5 aprobado."""
    e = e.upper()
    if any(k in e for k in ("PUBLICADA", "AUTÓGRAFA", "APROBADO")):
        return 5
    if "AGENDA" in e or "DEBATE" in e:
        return 4
    if "DICTAMEN" in e:
        return 3
    if "COMISIÓN" in e or "REMITIDA" in e:
        return 2
    if "ARCHIV" in e or "RETIRADO" in e:
        return 0
    return 1


def main():
    SALIDA.mkdir(parents=True, exist_ok=True)
    props = pd.read_csv(DATA / "proposiciones.csv", dtype=str).fillna("")
    temas = pd.read_csv(DATA / "temas.csv", dtype=str).fillna("")
    df = props.merge(temas[["camara", "pl_id", "tema", "temas_secundarios"]], on=["camara", "pl_id"], how="left").fillna("")

    lecturas = {}
    for j in leer_jsonl(DATA / "riesgo.jsonl"):
        lecturas[(j["camara"], j["pl_id"])] = {**j, "revisado_por": "modelo"}
    for j in leer_jsonl(DATA / "revision.jsonl"):  # la última revisión gana; las de checklist reemplazan a las viejas
        k = (j["camara"], j["pl_id"])
        if "preguntas" in j or lecturas.get(k, {}).get("revisado_por") != "agente" or "preguntas" not in lecturas[k]:
            lecturas[k] = {**j, "revisado_por": "agente"}

    movs = pd.read_csv(DATA / "movimientos.csv", dtype=str).fillna("")
    recorrido = {k: g[["seg_fecha", "seg_estado", "seg_detalle"]].values.tolist()
                 for k, g in movs.groupby(["camara", "pl_id"])}

    proyectos = []
    for r in df.itertuples():
        k = (r.camara, r.pl_id)
        lec = lecturas.get(k)
        proyectos.append({
            "id": f"{r.camara[0]}-{r.pl_id}", "camara": r.camara, "pl": r.pl_id, "fecha": r.fecha_presentacion,
            "titulo": r.titulo, "sumilla": r.sumilla, "tema": r.tema, "temas2": r.temas_secundarios,
            "bancada": r.grupo_parlamentario or "Sin bancada", "autor": r.autor_principal or r.proponente,
            "coautores": r.coautores, "comision": r.comisiones, "estado": r.ultimo_estado,
            "avance": estado_simple(r.ultimo_estado), "pdf": r.pdf_proyecto, "url": r.url,
            "recorrido": recorrido.get(k, []),
            "lectura": None if not lec else {
                "semaforo": lec["semaforo"], "resumen": lec.get("resumen", ""), "explicacion": lec.get("explicacion", ""),
                "derechos": lec.get("derechos", []), "estandares": lec.get("estandares", []),
                "cita": lec.get("cita_textual", ""), "cita_ok": bool(lec.get("cita_verificada")),
                "por": lec["revisado_por"], "revisar": bool(lec.get("revisar")) and lec["revisado_por"] == "modelo",
                "preguntas": lec.get("preguntas"), "ganan": lec.get("ganan", ""), "pierden": lec.get("pierden", ""),
            },
        })

    vot = pd.read_csv(DATA / "votaciones.csv", dtype=str).fillna("")
    vot = vot[vot.tipo != "Asistencia"]
    con_tabla = set((vot[vot.tipo == "Votación"].movimiento + vot[vot.tipo == "Votación"].proposiciones))
    vot = vot[(vot.tipo == "Votación") | ~(vot.movimiento + vot.proposiciones).isin(con_tabla)]
    vot = vot.drop_duplicates(["proposiciones", "movimiento", "a_favor", "en_contra"])
    votos = pd.read_csv(DATA / "votos.csv", dtype=str).fillna("")
    votaciones = []
    for v in vot.itertuples():
        nominal = votos[(votos.pdf == v.pdf) & (votos.pagina == v.pagina)]
        votaciones.append({
            "id": f"{v.pdf}-{v.pagina}", "camara": v.camara, "pls": v.proposiciones.split("; "), "fecha": v.fecha,
            "tipo": v.tipo, "asunto": v.asunto, "movimiento": v.movimiento, "resultado": v.resultado,
            "si": v.a_favor, "no": v.en_contra, "abst": v.abstencion,
            "bancadas": json.loads(v.votos_por_bancada) if v.votos_por_bancada else None,
            "control": v.control, "fuente": v.fuente, "url": v.url,
            "votos": nominal[["congresista", "bancada", "codigo"]].values.tolist(),
        })

    maestro = pd.read_csv(DATA / "maestro_congresistas.csv", dtype=str)
    meta = {"actualizado": max(df.fecha_presentacion), "n_proyectos": len(df), "n_lecturas": len(lecturas),
            "n_votaciones": len(votaciones),
            "bancadas": dict(zip(maestro.bancada, maestro.bancada_nombre)),
            "preguntas": [{"id": i, "dimension": d, "texto": t, "critica": c} for i, d, t, c in PREGUNTAS]}

    for nombre, obj in (("proyectos.json", proyectos), ("votaciones.json", votaciones), ("meta.json", meta)):
        (SALIDA / nombre).write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"site/data: {len(proyectos)} proyectos, {len(lecturas)} lecturas, {len(votaciones)} votaciones")


if __name__ == "__main__":
    main()
