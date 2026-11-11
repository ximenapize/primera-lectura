# comparar_modelos.py
# Compara dos primeras lecturas (por ejemplo qwen2.5 y qwen3) contra la segunda lectura de Claude Sonnet,
# y arma la lista de verdes que conviene revisar: los que el otro modelo marcó como alerta, más una muestra al azar.
# Uso: uv run ai/comparar_modelos.py data/riesgo.jsonl data/riesgo_qwen3.jsonl
import json
import sys
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]


def leer(ruta) -> pd.DataFrame:
    filas = [json.loads(l) for l in Path(ruta).read_text(encoding="utf-8").splitlines() if l]
    return pd.DataFrame(filas).drop_duplicates(["camara", "pl_id"], keep="last").set_index(["camara", "pl_id"])


a, b = leer(sys.argv[1]), leer(sys.argv[2])
sonnet = leer(RAIZ / "data" / "revision.jsonl")
sonnet = sonnet[sonnet.get("preguntas").notna()] if "preguntas" in sonnet else sonnet
comun = a.index.intersection(b.index)
print(f"Proyectos leídos por ambos modelos: {len(comun)}\n")
print("Colores (filas: modelo A, columnas: modelo B)")
print(pd.crosstab(a.loc[comun, "semaforo"], b.loc[comun, "semaforo"], margins=True), "\n")

for nombre, m in [("A", a), ("B", b)]:
    juntos = m.index.intersection(sonnet.index)
    acierto = (m.loc[juntos, "semaforo"] == sonnet.loc[juntos, "semaforo"]).mean()
    citas = m.loc[comun, "cita_verificada"].mean()
    print(f"Modelo {nombre}: coincide con Sonnet en {acierto:.0%} de {len(juntos)} revisados; citas verificadas {citas:.0%}")

# verdes de A que B ve como alerta: candidatos a que se le escapó algo a A
sospechosos = [i for i in comun if a.loc[i, "semaforo"] == "verde" and b.loc[i, "semaforo"] != "verde"]
verdes = [i for i in comun if a.loc[i, "semaforo"] == "verde" and i not in sospechosos]
muestra = pd.Series(verdes).sample(n=min(30, len(verdes)), random_state=7).tolist()
salida = RAIZ / "data" / "verdes_a_revisar.txt"
salida.write_text("\n".join(f"{c},{p}" for c, p in sospechosos + muestra) + "\n")
print(f"\n{len(sospechosos)} verdes que el modelo B marca como alerta + {len(muestra)} verdes al azar -> {salida}")
