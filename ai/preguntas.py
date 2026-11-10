# preguntas.py
# Las 15 preguntas guía de la rúbrica de riesgo (lente: derechos humanos y gobernanza) y la regla que convierte
# sus respuestas en el semáforo. Las usan la primera lectura (ai/riesgo.py), la segunda lectura del agente
# (ai/revision.py) y el sitio. El color NO lo decide el modelo: sale de estas respuestas.
#
# Respuestas posibles: "si", "no", "depende" (el efecto depende de la implementación o de un reglamento) y
# "no_aplica". Cada pregunta "crítica" respondida "si" vuelve rojo el proyecto.

PREGUNTAS = [
    # (id, dimensión, texto, crítica)
    ("vulnerables", "Personas afectadas",
     "¿Afecta a grupos en situación de vulnerabilidad (niñez, mujeres, pueblos indígenas y afroperuanos, personas "
     "con discapacidad, adultos mayores, personas LGTBI, migrantes, personas privadas de libertad, defensores de DDHH)?",
     False),
    ("restringe", "Contenido del derecho",
     "¿Restringe, suspende o elimina un derecho reconocido?", False),
    ("no_proporcional", "Contenido del derecho",
     "Si restringe un derecho, ¿falla el test de proporcionalidad (finalidad legítima, idoneidad, necesidad, "
     "proporcionalidad en sentido estricto)?", True),
    ("regresiva", "Contenido del derecho",
     "¿Es regresiva: reduce un nivel de protección ya alcanzado (principio de progresividad y no regresión)?", True),
    ("contra_constitucion", "Estándares",
     "¿Contradice la Constitución o la jurisprudencia del Tribunal Constitucional?", True),
    ("contra_tratado", "Estándares",
     "¿Contradice un tratado ratificado (CADH, PIDCP, PIDESC, CDN, CEDAW, Convenio 169) o la jurisprudencia de la "
     "Corte IDH, incluidas las sentencias contra el Perú?", True),
    ("equilibrio_poderes", "Institucionalidad democrática",
     "¿Altera el equilibrio de poderes: concentra facultades, limita el control político o judicial, o permite que "
     "un poder elija o remueva a los integrantes de otro?", True),
    ("reglas_electorales", "Institucionalidad democrática",
     "¿Cambia reglas electorales o de representación cerca de una elección, o a favor de quienes la aprueban?", True),
    ("rendicion_cuentas", "Institucionalidad democrática",
     "¿Debilita la rendición de cuentas, la transparencia o la lucha contra la corrupción?", False),
    ("espacio_civico", "Espacio cívico y participación",
     "¿Restringe a la sociedad civil, las ONG, la cooperación internacional, la prensa o la protesta?", True),
    ("sin_consulta", "Espacio cívico y participación",
     "¿Requería consulta previa (si afecta a pueblos indígenas) o participación ciudadana, y no la prevé?", True),
    ("retroactiva", "Calidad de la norma",
     "¿Tiene efectos retroactivos desfavorables?", True),
    ("gasto_sin_fondos", "Implementación e impacto",
     "¿Crea gasto sin financiamiento o choca con la regla fiscal?", False),
    ("impacto_ambiental", "Implementación e impacto",
     "¿Tiene impacto ambiental sin evaluación (bosques, minería informal, áreas protegidas)?", False),
]
# La pregunta abierta "¿quiénes ganan y quiénes pierden?" va aparte, como texto libre (campos "ganan" y "pierden").

IDS = [p[0] for p in PREGUNTAS]
CRITICAS = {p[0] for p in PREGUNTAS if p[3]}
RESPUESTAS = ["si", "no", "depende", "no_aplica"]


def esquema_preguntas() -> dict:
    """JSON Schema del bloque de respuestas: una propiedad por pregunta, con las cuatro respuestas posibles."""
    return {
        "type": "object",
        "properties": {i: {"type": "string", "enum": RESPUESTAS} for i in IDS},
        "required": IDS,
        "additionalProperties": False,
    }


def semaforo(respuestas: dict) -> str:
    """Regla fija: un "si" crítico es rojo; un "si" de contexto o un "depende" es amarillo; si no, verde.
    "no_proporcional" solo cuenta si además el proyecto restringe un derecho."""
    r = {i: respuestas.get(i, "no_aplica") for i in IDS}
    if r["restringe"] not in ("si", "depende") and r["no_proporcional"] == "si":
        r["no_proporcional"] = "no_aplica"  # sin restricción no hay test que fallar
    if any(r[i] == "si" for i in CRITICAS):
        return "rojo"
    if any(v == "si" for i, v in r.items() if i not in CRITICAS and i != "restringe") or \
            any(v == "depende" for v in r.values()):
        return "amarillo"
    return "verde"


def activadas(respuestas: dict) -> list:
    """Preguntas respondidas "si" o "depende", para mostrarlas en la ficha."""
    return [i for i in IDS if respuestas.get(i) in ("si", "depende")]


if __name__ == "__main__":
    print(f"{len(PREGUNTAS)} preguntas, {len(CRITICAS)} críticas: {sorted(CRITICAS)}")
    assert semaforo({i: "no" for i in IDS}) == "verde"
    assert semaforo({**{i: "no" for i in IDS}, "vulnerables": "si"}) == "amarillo"
    assert semaforo({**{i: "no" for i in IDS}, "restringe": "si", "no_proporcional": "si"}) == "rojo"
    assert semaforo({**{i: "no" for i in IDS}, "restringe": "no", "no_proporcional": "si"}) == "verde"
    assert semaforo({**{i: "no" for i in IDS}, "restringe": "si"}) == "verde"
    assert semaforo({**{i: "no" for i in IDS}, "gasto_sin_fondos": "depende"}) == "amarillo"
    print("reglas OK")
