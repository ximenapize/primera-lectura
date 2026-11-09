# riesgo.py
# "Primera lectura" de un proyecto de ley: lee la fórmula legal del PDF con un LLM local y devuelve un
# semáforo de riesgo frente a derechos humanos y estándares de gobernanza, con la cita textual que lo
# sustenta. Python verifica que la cita exista en el PDF (el modelo no puede inventarla).
# Guarda en data/riesgo.jsonl (una línea por proposición) y es incremental.
# Uso: uv run ai/riesgo.py --ids 00761-2026-2031-CD,00757-2026-2031-CD
#      uv run ai/riesgo.py --prefiltro          (solo los que pasan el filtro de reglas)
import argparse
import json
import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from llm import MODELO, preguntar  # noqa: E402
from pdf_texto import cita_verificada, partes, texto_pdf  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
PROPS = RAIZ / "data" / "proposiciones.csv"
TEMAS = RAIZ / "data" / "temas.csv"
SALIDA = RAIZ / "data" / "riesgo.jsonl"

DERECHOS = [
    "Igualdad y no discriminación", "Libertad de expresión y prensa", "Acceso a la información pública",
    "Debido proceso y tutela judicial", "Independencia judicial y separación de poderes",
    "Derechos políticos y elecciones", "Libertad de asociación y sociedad civil", "Protesta y reunión",
    "Integridad, libertad personal y uso de la fuerza", "Pueblos indígenas y consulta previa",
    "Derechos de las mujeres", "Niñez y adolescencia", "Ambiente sano", "Salud", "Educación",
    "Derechos laborales y seguridad social", "Lucha contra la corrupción y rendición de cuentas",
    "Sostenibilidad fiscal", "Ninguno",
]

# El orden importa: el modelo escribe primero el resumen, la cita y su razonamiento, y recién al final
# decide los derechos y el semáforo (así la conclusión sale de lo que leyó, no al revés).
ESQUEMA = {
    "type": "object",
    "properties": {
        "resumen": {"type": "string"},
        "cita_textual": {"type": "string"},
        "explicacion": {"type": "string"},
        "derechos": {"type": "array", "items": {"type": "string", "enum": DERECHOS}, "maxItems": 3},
        "estandares": {"type": "array", "items": {"type": "string"}, "maxItems": 3},
        "semaforo": {"type": "string", "enum": ["verde", "amarillo", "rojo"]},
    },
    "required": ["resumen", "cita_textual", "explicacion", "derechos", "estandares", "semaforo"],
}

SISTEMA = """Eres abogada experta en derechos humanos y gobernanza que hace la primera lectura de proyectos de ley \
del Congreso del Perú para una consultora. Lees la fórmula legal y evalúas si, de aprobarse, podría vulnerar \
derechos humanos o estándares de gobernanza nacionales e internacionales.

Semáforo:
- rojo: restringe o retrocede claramente un derecho o un estándar (por ejemplo, limita la fiscalización, \
debilita la independencia judicial, criminaliza la protesta, restringe a ONG o a la prensa, discrimina, \
omite la consulta previa, reduce protecciones ambientales o laborales, amnistía graves violaciones).
- amarillo: toca un derecho o estándar y su efecto depende de cómo se implemente, o tiene impacto fiscal sin financiamiento.
- verde: no afecta derechos ni estándares de forma relevante, o los amplía.

Estándares de referencia: Constitución Política del Perú, Convención Americana sobre Derechos Humanos y \
jurisprudencia de la Corte IDH, Pacto Internacional de Derechos Civiles y Políticos, PIDESC, Convenio 169 de la OIT, \
CEDAW, Convención sobre los Derechos del Niño, Acuerdo de Escazú, Convención de la ONU contra la Corrupción, \
Principios de gobernanza de la OCDE, Regla fiscal (Decreto Legislativo 1276).

Reglas:
- cita_textual: copia EXACTAMENTE una frase de la fórmula legal (entre 10 y 40 palabras) que sustente tu evaluación.
- estandares: cita el instrumento y el artículo, por ejemplo "CADH, art. 13". Si es verde, puede ir vacío.
- explicacion: máximo 3 frases, concretas, sin adjetivos innecesarios.
- resumen: qué cambia el proyecto, en una frase que entienda cualquier persona.
- No exageres: la mayoría de proyectos son verdes. Responde en español."""


def analizar(fila) -> dict:
    texto = texto_pdf(fila.pdf_proyecto, f"{fila.camara}_{fila.pl_id}")
    p = partes(texto)
    usuario = (f"Proyecto {fila.pl_id} ({fila.camara}). Título: {fila.titulo}\n"
               f"Sumilla: {fila.sumilla}\n\nFÓRMULA LEGAL:\n{p['formula']}\n\n"
               f"INICIO DE LA EXPOSICIÓN DE MOTIVOS:\n{p['motivos']}")
    r = preguntar(SISTEMA, usuario, ESQUEMA, contexto=8192)
    r["derechos"] = [d for d in r["derechos"] if d != "Ninguno"]
    if r["semaforo"] == "verde":
        r["derechos"], r["estandares"] = [], []
    r["cita_verificada"] = cita_verificada(r["cita_textual"], texto)
    # pasa a revisión humana o del agente revisor si es rojo/amarillo sin sustento completo
    r["revisar"] = r["semaforo"] != "verde" and not (r["derechos"] and r["estandares"] and r["cita_verificada"])
    r["pdf_legible"] = p["legible"]
    return r


def prefiltro(props: pd.DataFrame) -> pd.DataFrame:
    """Reglas baratas antes del LLM: proyectos vigentes de temáticas sensibles o con palabras de alerta.
    Ordenados por prioridad: primero los que avanzan (dictamen, agenda del pleno), luego los más recientes."""
    temas = pd.read_csv(TEMAS, dtype=str).fillna("")
    df = props.merge(temas[["camara", "pl_id", "tema", "temas_secundarios"]], on=["camara", "pl_id"], how="left")
    sensibles = ["Justicia y derechos humanos", "Seguridad y defensa", "Estado y reforma política",
                 "Inclusión social, mujer y pueblos indígenas", "Medio ambiente", "Minería y energía"]
    claves = (r"protesta|\bong\b|cooperación técnica internacional|apci|prensa|periodis|consulta previa|indígena|"
              r"amnist|prescripci|lesa humanidad|fuerzas armadas|uso de la fuerza|tribunal constitucional|"
              r"junta nacional de justicia|fiscalía|ministerio público|contralor|defensoría|migra|extranjer|"
              r"aborto|pena de muerte|cadena perpetua|castración|bosque|deforest|minería informal|reinfo|"
              r"transparencia|acceso a la información|libertad de expresión|corte interamericana|"
              r"igualdad de género|enfoque de género|lgtb|identidad de género|sindica|huelga")
    texto = (df.titulo + " " + df.sumilla).str.lower()
    vigente = ~df.ultimo_estado.str.contains("Archivad|Retirad", regex=True)
    mascara = vigente & (df.tema.isin(sensibles) | texto.str.contains(claves, regex=True))
    df = df[mascara & (df.tema != "Declaraciones y homenajes")].copy()
    avanza = df.ultimo_estado.str.contains("DICTAMEN|AGENDA|APROBADO|Autógrafa", case=False, regex=True)
    df["_prioridad"] = (~avanza).astype(int)
    return df.sort_values(["_prioridad", "fecha_presentacion"], ascending=[True, False]).drop(columns="_prioridad")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", default="", help="pl_id separados por coma")
    ap.add_argument("--prefiltro", action="store_true")
    ap.add_argument("--limite", type=int, default=None)
    a = ap.parse_args()

    props = pd.read_csv(PROPS, dtype=str).fillna("")
    if a.ids:
        objetivo = props[props.pl_id.isin(a.ids.split(","))]
    elif a.prefiltro:
        objetivo = prefiltro(props)
    else:
        objetivo = props
    hechos = set()
    if SALIDA.exists():
        hechos = {(j["camara"], j["pl_id"]) for j in map(json.loads, SALIDA.read_text().splitlines())}
    objetivo = objetivo[[(c, p) not in hechos for c, p in zip(objetivo.camara, objetivo.pl_id)]]
    if a.limite:
        objetivo = objetivo.head(a.limite)
    print(f"{len(objetivo)} proposiciones por analizar con {MODELO}")

    t0 = time.time()
    with open(SALIDA, "a", encoding="utf-8") as f:
        for i, fila in enumerate(objetivo.itertuples(), 1):
            try:
                r = analizar(fila)
            except Exception as e:
                print(f"[{i}/{len(objetivo)}] {fila.pl_id} ERROR {e}")
                continue
            f.write(json.dumps({"camara": fila.camara, "pl_id": fila.pl_id, **r, "modelo": MODELO},
                               ensure_ascii=False) + "\n")
            f.flush()
            print(f"[{i}/{len(objetivo)}] {fila.pl_id} {r['semaforo'].upper():8} cita_ok={r['cita_verificada']} "
                  f"({(time.time() - t0) / i:.0f} s/u)")


if __name__ == "__main__":
    main()
