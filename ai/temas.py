# temas.py
# Asigna a cada proposición una temática principal (y hasta dos secundarias) leyendo título y sumilla
# con un LLM local. La comisión que ya trae el portal va como pista, no como respuesta.
# Guarda en data/temas.csv y es incremental: solo clasifica lo que aún no está.
# Uso: uv run ai/temas.py   (opciones: --limite N)
import argparse
import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from llm import MODELO, preguntar  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
ENTRADA = RAIZ / "data" / "proposiciones.csv"
SALIDA = RAIZ / "data" / "temas.csv"

TEMAS = [
    "Economía y finanzas", "Trabajo y pensiones", "Salud", "Educación y cultura",
    "Justicia y derechos humanos", "Seguridad y defensa", "Estado y reforma política",
    "Gobiernos regionales y locales", "Infraestructura y transporte", "Minería y energía",
    "Medio ambiente", "Agro y pesca", "Inclusión social, mujer y pueblos indígenas",
    "Producción, comercio y turismo", "Consumidor y servicios públicos", "Tecnología y digital",
    "Declaraciones y homenajes",
]

ESQUEMA = {
    "type": "object",
    "properties": {
        "tema": {"type": "string", "enum": TEMAS},
        "temas_secundarios": {"type": "array", "items": {"type": "string", "enum": TEMAS}, "maxItems": 2},
    },
    "required": ["tema", "temas_secundarios"],
}

SISTEMA = (
    "Eres analista legislativo en el Perú. Clasificas proyectos de ley por la materia que regulan, "
    "como lo haría una consultora de asuntos públicos. Elige UNA temática principal de la lista y, solo si "
    "el proyecto toca claramente otras materias, hasta dos secundarias. Los proyectos que declaran de interés "
    "nacional una obra van en la materia de la obra (por ejemplo, una carretera es Infraestructura). "
    "Elecciones, partidos, Congreso, procedimiento administrativo y organización del Estado van en "
    "'Estado y reforma política'. Delitos, penas, Poder Judicial, Fiscalía y derechos fundamentales van en "
    "'Justicia y derechos humanos'. "
    "Usa 'Declaraciones y homenajes' solo para días conmemorativos, patrimonio simbólico u homenajes.\n"
    "Temáticas: " + "; ".join(TEMAS)
)


def clasificar(fila: pd.Series) -> dict:
    usuario = (f"Título: {fila.titulo}\nSumilla: {fila.sumilla or '(sin sumilla)'}\n"
               f"Comisión asignada (pista): {fila.comisiones or '(ninguna)'}")
    r = preguntar(SISTEMA, usuario, ESQUEMA, contexto=2048)
    secundarios = [t for t in r.get("temas_secundarios", []) if t != r["tema"]]
    return {"tema": r["tema"], "temas_secundarios": "; ".join(dict.fromkeys(secundarios))}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--limite", type=int, default=None)
    a = p.parse_args()

    props = pd.read_csv(ENTRADA, dtype=str).fillna("")
    hechos = pd.read_csv(SALIDA, dtype=str).fillna("") if SALIDA.exists() else pd.DataFrame(
        columns=["camara", "pl_id", "tema", "temas_secundarios", "modelo"])
    ya = set(zip(hechos.camara, hechos.pl_id))
    pendientes = props[[(c, p) not in ya for c, p in zip(props.camara, props.pl_id)]]
    if a.limite:
        pendientes = pendientes.head(a.limite)
    print(f"{len(pendientes)} por clasificar con {MODELO}")

    nuevas, t0 = [], time.time()
    for i, fila in enumerate(pendientes.itertuples(), 1):
        nuevas.append({"camara": fila.camara, "pl_id": fila.pl_id, **clasificar(fila), "modelo": MODELO})
        print(f"[{i}/{len(pendientes)}] {fila.pl_id} -> {nuevas[-1]['tema']}  ({(time.time() - t0) / i:.1f} s/u)")
        if i % 25 == 0 or i == len(pendientes):  # guarda cada 25 por si se interrumpe
            pd.concat([hechos, pd.DataFrame(nuevas)]).to_csv(SALIDA, index=False)


if __name__ == "__main__":
    main()
