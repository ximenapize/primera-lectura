---
name: revisando-alertas
description: Revisa las alertas rojas y amarillas que el modelo local (qwen2.5) puso a los proyectos de ley de Primera Lectura, aplicando la rúbrica pública de ai/rubrica.md. Confirma o corrige el semáforo, los derechos, los estándares y la cita. Úsala cuando pidan "revisa las alertas", "segunda lectura" o "revisa los rojos".
---

# Revisando alertas (segunda lectura)

El modelo local hace la **primera lectura** de cada proyecto de ley y se equivoca a menudo: etiqueta derechos que
no corresponden, cita artículos inexistentes, copia títulos de sección como "cita" o lee al revés la dirección de
una derogación. Tú haces la **segunda lectura** solo sobre las alertas rojas y amarillas, **aplicando la rúbrica**.

## Antes de empezar

Lee completa la rúbrica: [`ai/rubrica.md`](../../../ai/rubrica.md). Ahí están los pasos (qué cambia, dirección,
test de proporcionalidad, semáforo), los instrumentos de referencia por derecho y ejemplos de cada color.

## Pasos

1. `uv run ai/revision.py estado [--semaforo rojo] [--parte 1/2]` para ver cuántas faltan en tu lote.
2. `uv run ai/revision.py pendientes --n 5 [--semaforo rojo] [--parte 1/2]` trae un lote en JSON: título,
   sumilla, `formula_legal` (lo que cambiaría la ley) y la `lectura_modelo_local`.
3. Por cada proyecto aplica la rúbrica:
   - **Qué cambia:** léelo en `formula_legal`, no en la sumilla.
   - **Dirección:** ¿restringe o amplía? Una derogación de una norma restrictiva amplía derechos (verde).
   - **Test de proporcionalidad** si restringe: finalidad legítima, idoneidad, necesidad, proporcionalidad.
   - **Semáforo:** rojo solo si retrocede claramente o falla el test; ante la duda, amarillo.
   - **Derechos:** hasta 3, solo de la lista `DERECHOS` de `ai/riesgo.py`. Vacío si es verde.
   - **Estándares:** del cuadro de instrumentos de la rúbrica, con artículo solo si estás seguro. Vacío si es verde.
   - **Cita textual:** una frase copiada EXACTA de `formula_legal` (10 a 40 palabras). Nunca un título de sección.
   - **Explicación:** máximo 3 frases sobrias para una consultora; menciona el paso del test que falla, si aplica.
   - **Resumen:** qué cambia el proyecto, en una frase que entienda cualquier persona.
   - Si `formula_legal` viene vacía o ilegible (PDF escaneado), basa la revisión en título y sumilla, deja la cita
     vacía y dilo en la explicación.
4. Guarda cada revisión pasando el JSON por la entrada estándar (así los apóstrofes no rompen el comando):
   ```bash
   uv run ai/revision.py guardar - --modelo "Claude Sonnet" <<'EOF'
   {"camara":"diputados","pl_id":"00589-2026-2031-CD","semaforo":"rojo","derechos":["Integridad, libertad personal y uso de la fuerza"],"estandares":["CADH, art. 7.5"],"cita_textual":"...","explicacion":"...","resumen":"..."}
   EOF
   ```
   El script valida los campos y verifica la cita en el PDF. Si responde `cita verificada: False`, corrige la
   cita (cópiala exacta de `formula_legal`) y vuelve a guardar: gana la última línea.
5. Repite hasta que `estado` diga 0 en tu lote. Al final informa: cuántas confirmaste, cuántas cambiaste de color
   (de qué a qué) y cuáles quedaron en rojo, con una línea de por qué.

## Reglas

- No inventes contenido que no esté en la fórmula legal ni artículos de instrumentos que no existan.
- No modifiques archivos del repositorio: solo usa `ai/revision.py`.
- Es una alerta temprana, no una opinión legal.
