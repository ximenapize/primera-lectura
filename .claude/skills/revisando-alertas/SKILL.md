---
name: revisando-alertas
description: Revisa las alertas rojas y amarillas que el modelo local (qwen2.5) puso a los proyectos de ley de Primera Lectura. Confirma o corrige el semáforo, los derechos, los estándares y la cita. Úsala cuando pidan "revisa las alertas", "segunda lectura" o "revisa los rojos".
---

# Revisando alertas (segunda lectura)

El modelo local hace la **primera lectura** de cada proyecto de ley y a veces se equivoca: etiqueta derechos
que no corresponden, cita artículos inexistentes o lee al revés la dirección de una derogación. Tú haces la
**segunda lectura** solo sobre las alertas rojas y amarillas.

## Pasos

1. `uv run ai/revision.py estado` para ver cuántas faltan.
2. `uv run ai/revision.py pendientes --n 5` trae un lote en JSON: título, sumilla, `formula_legal` (lo que
   cambiaría la ley) y la `lectura_modelo_local`.
3. Por cada proyecto, lee la fórmula legal y decide:
   - **Dirección**: ¿el proyecto restringe o amplía el derecho? Derogar una norma que restringía derechos
     es verde o amarillo, no rojo.
   - **Semáforo**:
     - **Rojo**: retrocede claramente un derecho o un estándar.
     - **Amarillo**: el efecto depende de la implementación, o tiene impacto fiscal sin financiamiento.
     - **Verde**: no afecta derechos, o los amplía.
   - **Derechos**: hasta 3, solo de la lista de `DERECHOS` en `ai/riesgo.py`.
   - **Estándares**: instrumento y artículo reales. Ejemplos: "CADH, art. 7.5 (control judicial de la
     detención)", "Convención sobre los Derechos del Niño, art. 40", "Constitución, art. 2.12",
     "Convenio 169 OIT, art. 6", "Acuerdo de Escazú, art. 7". Si no estás segura del número de artículo,
     cita solo el instrumento.
   - **Cita textual**: una frase copiada EXACTA de `formula_legal`, de 10 a 40 palabras.
   - **Explicación**: máximo 3 frases, sobrias, para una consultora. Sin adjetivos alarmistas.
   - **Resumen**: qué cambia el proyecto, en una frase.
4. Guarda cada revisión:
   ```bash
   uv run ai/revision.py guardar '{"camara":"diputados","pl_id":"00589-2026-2031-CD","semaforo":"rojo","derechos":["Integridad, libertad personal y uso de la fuerza"],"estandares":["CADH, art. 7.5"],"cita_textual":"...","explicacion":"...","resumen":"..."}'
   ```
   El script valida los campos y verifica que la cita exista en el PDF. Si responde `cita verificada: False`,
   corrige la cita y vuelve a guardar: gana la última línea.
5. Repite hasta que `estado` diga 0. Al final, informa cuántas alertas confirmaste, cuántas bajaste o subiste
   de color y cuáles son los rojos.

## Reglas

- No inventes contenido que no esté en la fórmula legal.
- Ante la duda entre rojo y amarillo, elige amarillo y explica de qué depende.
- Es una alerta temprana, no una opinión legal.
