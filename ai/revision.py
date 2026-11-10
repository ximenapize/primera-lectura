# revision.py
# Herramienta de la skill "revisando-alertas": el agente revisor (Claude Sonnet) hace la segunda lectura de las
# alertas del modelo local respondiendo el checklist de la rúbrica (ai/preguntas.py). El semáforo no lo elige el
# agente: lo calcula preguntas.semaforo() a partir de sus respuestas.
#   uv run ai/revision.py pendientes [--n 5] [--semaforo rojo] [--parte 1/2]  -> alertas sin revisar, con la fórmula legal
#   uv run ai/revision.py guardar - [--modelo sonnet] < revision.json         -> valida y agrega a data/revision.jsonl
#   uv run ai/revision.py estado [--semaforo rojo] [--parte 1/2]               -> cuántas faltan
import json
import sys
import zlib
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from pdf_texto import cita_verificada, partes, texto_pdf  # noqa: E402
from preguntas import IDS, PREGUNTAS, RESPUESTAS, activadas, semaforo  # noqa: E402
from riesgo import DERECHOS  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
RIESGO = RAIZ / "data" / "riesgo.jsonl"
REVISION = RAIZ / "data" / "revision.jsonl"
PROPS = RAIZ / "data" / "proposiciones.csv"


def leer_jsonl(ruta: Path) -> list:
    return [json.loads(l) for l in ruta.read_text(encoding="utf-8").splitlines() if l] if ruta.exists() else []


def pendientes(color: str = "", parte: str = "") -> pd.DataFrame:
    """Alertas rojas y amarillas sin segunda lectura. `parte` = "i/k" reparte el trabajo entre k revisores."""
    r = pd.DataFrame(leer_jsonl(RIESGO)).drop_duplicates(["camara", "pl_id"], keep="last")
    hechos = {(j["camara"], j["pl_id"]) for j in leer_jsonl(REVISION) if "preguntas" in j}
    r = r[r.semaforo.isin([color] if color else ["rojo", "amarillo"])]
    r = r.loc[[(c, p) not in hechos for c, p in zip(r.camara, r.pl_id)]]
    if parte:
        i, k = (int(x) for x in parte.split("/"))
        r = r.loc[[zlib.crc32(p.encode()) % k == i - 1 for p in r.pl_id]]
    return r.assign(_o=r.semaforo.map({"rojo": 0, "amarillo": 1})).sort_values("_o").drop(columns="_o")


def cmd_pendientes(n: int, semaforo: str = "", parte: str = ""):
    props = pd.read_csv(PROPS, dtype=str).fillna("").set_index(["camara", "pl_id"])
    salida = []
    for a in pendientes(semaforo, parte).head(n).to_dict("records"):
        p = props.loc[(a["camara"], a["pl_id"])]
        texto = texto_pdf(p.pdf_proyecto, f"{a['camara']}_{a['pl_id']}")
        salida.append({
            "camara": a["camara"], "pl_id": a["pl_id"], "titulo": p.titulo, "sumilla": p.sumilla,
            "formula_legal": partes(texto)["formula"],
            "lectura_modelo_local": {k: a[k] for k in ["semaforo", "derechos", "estandares", "cita_textual", "explicacion"]},
        })
    guia = {i: f"{texto}{' (CRÍTICA)' if critica else ''}" for i, _, texto, critica in PREGUNTAS}
    print(json.dumps({"preguntas_a_responder": guia, "respuestas_validas": RESPUESTAS, "proyectos": salida},
                     ensure_ascii=False, indent=1))


def cmd_guardar(crudo: str, modelo: str):
    j = json.loads(sys.stdin.read() if crudo == "-" else crudo)
    faltan = {"camara", "pl_id", "preguntas", "ganan", "pierden", "derechos", "estandares", "cita_textual",
              "explicacion", "resumen"} - set(j)
    if faltan:
        sys.exit(f"Faltan campos: {faltan}")
    malas = {i: j["preguntas"].get(i) for i in IDS if j["preguntas"].get(i) not in RESPUESTAS}
    if malas:
        sys.exit(f"Respuestas inválidas o faltantes en preguntas: {malas}. Cada una debe ser una de {RESPUESTAS}")
    j["preguntas"] = {i: j["preguntas"][i] for i in IDS}
    j["semaforo"] = semaforo(j["preguntas"])  # el color sale de las respuestas, no del agente
    j["activadas"] = activadas(j["preguntas"])
    if j["semaforo"] == "verde":
        j["derechos"], j["estandares"] = [], []
    malos = [d for d in j["derechos"] if d not in DERECHOS]
    if malos:
        sys.exit(f"Derechos fuera de la lista: {malos}. Usa: {DERECHOS}")
    props = pd.read_csv(PROPS, dtype=str).fillna("").set_index(["camara", "pl_id"])
    p = props.loc[(j["camara"], j["pl_id"])]
    texto = texto_pdf(p.pdf_proyecto, f"{j['camara']}_{j['pl_id']}")
    j["cita_verificada"] = cita_verificada(j["cita_textual"], texto) if j["cita_textual"] else False
    j["revisado_por"] = f"agente revisor ({modelo})"
    with open(REVISION, "a", encoding="utf-8") as f:
        f.write(json.dumps(j, ensure_ascii=False) + "\n")
    print(f"Guardado {j['pl_id']}: {j['semaforo']} (activadas: {', '.join(j['activadas']) or 'ninguna'}) · "
          f"cita verificada: {j['cita_verificada']}")


def opcion(nombre: str, defecto: str = "") -> str:
    return sys.argv[sys.argv.index(nombre) + 1] if nombre in sys.argv else defecto


if __name__ == "__main__":
    accion = sys.argv[1] if len(sys.argv) > 1 else "estado"
    if accion == "pendientes":
        cmd_pendientes(int(opcion("--n", "5")), opcion("--semaforo"), opcion("--parte"))
    elif accion == "guardar":  # el JSON va como argumento o, con "-", por la entrada estándar
        cmd_guardar(sys.argv[2], opcion("--modelo", "Claude Code"))
    else:
        print(f"{len(pendientes(opcion('--semaforo'), opcion('--parte')))} alertas sin revisar")
