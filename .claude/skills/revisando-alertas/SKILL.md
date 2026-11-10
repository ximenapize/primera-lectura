---
name: revisando-alertas
description: Hace la segunda lectura de los proyectos de ley que el modelo local (qwen2.5) marcó como alerta en Primera Lectura, respondiendo el checklist de la rúbrica pública (ai/rubrica.md, ai/preguntas.py). El semáforo sale de las respuestas. Úsala cuando pidan "revisa las alertas", "segunda lectura" o "aplica la rúbrica".
---

# Revisando alertas (segunda lectura con checklist)

El modelo local hace una primera lectura barata y se equivoca a menudo (lee al revés derogaciones, marca
regulaciones legítimas, copia títulos de sección como "cita"). Tú haces la **segunda lectura respondiendo el
checklist de la rúbrica**. **No eliges el color**: `ai/revision.py` lo calcula con la regla fija a partir de tus
respuestas.

## Antes de empezar

Lee completa la rúbrica: [`ai/rubrica.md`](../../../ai/rubrica.md) (dirección del efecto, test de
proporcionalidad, checklist, regla del semáforo, instrumentos por derecho y ejemplos).

## Pasos

1. `uv run ai/revision.py estado [--semaforo rojo|amarillo|verde] [--parte 1/3]` para ver cuántas faltan en tu lote.
2. `uv run ai/revision.py pendientes --n 4 [--semaforo ...] [--parte ...]` trae un JSON con
   `preguntas_a_responder` (id → texto, las críticas marcadas), `respuestas_validas` y `proyectos` (título,
   sumilla, `formula_legal` y la lectura del modelo local).
3. Por cada proyecto:
   - Lee `formula_legal` y decide **qué cambia y en qué dirección**. Si amplía un derecho o deroga una norma
     restrictiva, las preguntas de riesgo son "no".
   - Responde **las 14 preguntas** con `si`, `no`, `depende` o `no_aplica`. Ante la duda en una pregunta crítica,
     `depende` (y explica de qué depende).
   - `ganan` y `pierden`: quiénes se benefician y quiénes se perjudican, en pocas palabras.
   - `derechos`: hasta 3, solo de la lista `DERECHOS` de `ai/riesgo.py` (vacío si nada se activa).
   - `estandares`: instrumentos del cuadro de la rúbrica, con artículo solo si estás seguro.
   - `cita_textual`: frase copiada EXACTA de `formula_legal` (10 a 40 palabras), nunca un título de sección. Si
     `formula_legal` viene vacía, ilegible o no es el articulado, deja la cita vacía y dilo en la explicación
     (basa la revisión en título y sumilla).
   - `explicacion`: máximo 3 frases; nombra las preguntas que respondiste "sí" o "depende" y por qué.
   - `resumen`: qué cambia el proyecto, en una frase para cualquier persona.
4. Guarda cada revisión por la entrada estándar:
   ```bash
   uv run ai/revision.py guardar - --modelo "Claude Sonnet" <<'EOF'
   {"camara":"diputados","pl_id":"00589-2026-2031-CD",
    "preguntas":{"vulnerables":"no","restringe":"si","no_proporcional":"si","regresiva":"si","contra_constitucion":"depende","contra_tratado":"si","equilibrio_poderes":"no","reglas_electorales":"no_aplica","rendicion_cuentas":"no","espacio_civico":"no","sin_consulta":"no_aplica","retroactiva":"no","gasto_sin_fondos":"no","impacto_ambiental":"no_aplica"},
    "ganan":"...","pierden":"...","derechos":["Integridad, libertad personal y uso de la fuerza"],
    "estandares":["CADH, art. 7.5"],"cita_textual":"...","explicacion":"...","resumen":"..."}
   EOF
   ```
   El script valida, **calcula el semáforo** y verifica la cita en el PDF. Si responde `cita verificada: False`
   con una cita no vacía, corrígela y vuelve a guardar: gana la última línea.
5. Repite hasta que `estado` diga 0 en tu lote. Al final informa: cuántos quedaron en rojo, amarillo y verde,
   qué preguntas críticas se activaron más, y los rojos con una línea de por qué.

## Reglas

- No inventes contenido que no esté en la fórmula legal ni artículos que no existan.
- No modifiques archivos del repositorio: solo usa `ai/revision.py`.
- Es una alerta temprana, no una opinión legal.
