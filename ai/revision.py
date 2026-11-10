# revision.py
# Herramienta de la skill "revisando-alertas": el agente revisor (Claude Code) relee las alertas rojas y
# amarillas del modelo local y las confirma o corrige.
#   uv run ai/revision.py pendientes [--n 5]   -> imprime en JSON las alertas aún sin revisar, con la fórmula legal
#   uv run ai/revision.py guardar '<json>'     -> valida y agrega una revisión a data/revision.jsonl
#   uv run ai/revision.py estado               -> cuántas faltan
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from pdf_texto import cita_verificada, partes, texto_pdf  # noqa: E402
from riesgo import DERECHOS  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
RIESGO = RAIZ / "data" / "riesgo.jsonl"
REVISION = RAIZ / "data" / "revision.jsonl"
PROPS = RAIZ / "data" / "proposiciones.csv"


def leer_jsonl(ruta: Path) -> list:
    return [json.loads(l) for l in ruta.read_text(encoding="utf-8").splitlines() if l] if ruta.exists() else []


def pendientes() -> pd.DataFrame:
    r = pd.DataFrame(leer_jsonl(RIESGO)).drop_duplicates(["camara", "pl_id"], keep="last")
    hechos = {(j["camara"], j["pl_id"]) for j in leer_jsonl(REVISION)}
    r = r[r.semaforo.isin(["rojo", "amarillo"])]
    r = r[[(c, p) not in hechos for c, p in zip(r.camara, r.pl_id)]]
    return r.assign(_o=r.semaforo.map({"rojo": 0, "amarillo": 1})).sort_values("_o").drop(columns="_o")


def cmd_pendientes(n: int):
    props = pd.read_csv(PROPS, dtype=str).fillna("").set_index(["camara", "pl_id"])
    salida = []
    for a in pendientes().head(n).to_dict("records"):
        p = props.loc[(a["camara"], a["pl_id"])]
        texto = texto_pdf(p.pdf_proyecto, f"{a['camara']}_{a['pl_id']}")
        salida.append({
            "camara": a["camara"], "pl_id": a["pl_id"], "titulo": p.titulo, "sumilla": p.sumilla,
            "formula_legal": partes(texto)["formula"],
            "lectura_modelo_local": {k: a[k] for k in ["semaforo", "derechos", "estandares", "cita_textual", "explicacion"]},
        })
    print(json.dumps(salida, ensure_ascii=False, indent=1))


def cmd_guardar(crudo: str):
    j = json.loads(crudo)
    faltan = {"camara", "pl_id", "semaforo", "derechos", "estandares", "cita_textual", "explicacion", "resumen"} - set(j)
    if faltan:
        sys.exit(f"Faltan campos: {faltan}")
    if j["semaforo"] not in ("verde", "amarillo", "rojo"):
        sys.exit("semaforo debe ser verde, amarillo o rojo")
    malos = [d for d in j["derechos"] if d not in DERECHOS]
    if malos:
        sys.exit(f"Derechos fuera de la lista: {malos}. Usa: {DERECHOS}")
    props = pd.read_csv(PROPS, dtype=str).fillna("").set_index(["camara", "pl_id"])
    p = props.loc[(j["camara"], j["pl_id"])]
    texto = texto_pdf(p.pdf_proyecto, f"{j['camara']}_{j['pl_id']}")
    j["cita_verificada"] = cita_verificada(j["cita_textual"], texto) if j["cita_textual"] else False
    j["revisado_por"] = "agente revisor (Claude Code)"
    with open(REVISION, "a", encoding="utf-8") as f:
        f.write(json.dumps(j, ensure_ascii=False) + "\n")
    print(f"Guardado {j['pl_id']}: {j['semaforo']} · cita verificada: {j['cita_verificada']}")


if __name__ == "__main__":
    accion = sys.argv[1] if len(sys.argv) > 1 else "estado"
    if accion == "pendientes":
        cmd_pendientes(int(sys.argv[sys.argv.index("--n") + 1]) if "--n" in sys.argv else 5)
    elif accion == "guardar":
        cmd_guardar(sys.argv[2])
    else:
        print(f"{len(pendientes())} alertas sin revisar")
