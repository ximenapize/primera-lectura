# Rúbrica de riesgo de Primera Lectura

Criterio público con el que la IA (primera lectura) y el agente revisor (segunda lectura) clasifican un proyecto
de ley. Existe para que el semáforo no dependa de quién lo lea: cualquiera puede revisar si se aplicó bien.

Lente actual: **derechos humanos y gobernanza**. Otros clientes pueden tener otro lente (riesgo regulatorio,
impacto sectorial); la estructura de la rúbrica es la misma.

## Paso 1. ¿Qué cambia el proyecto?

Leer la **fórmula legal** (el articulado), no la sumilla. Resumir en una frase qué norma crea, modifica o deroga.

## Paso 2. ¿En qué dirección va?

- **Restringe** un derecho o debilita un control → puede ser rojo o amarillo.
- **Amplía** un derecho o fortalece un control → verde.
- **Derogaciones:** mirar qué decía la norma derogada. Derogar una ley que *restringía* derechos (por ejemplo,
  una que limitaba la persecución de lesa humanidad o que exigía condena previa para la extinción de dominio)
  **amplía** la protección: es verde.
- Regular una actividad (licencias, requisitos, registros) no es por sí mismo una restricción de derechos.

## Paso 3. Test de proporcionalidad (solo si restringe)

Es el estándar que usan el Tribunal Constitucional y la Corte Interamericana:

1. **Finalidad legítima:** ¿persigue un fin constitucional (seguridad, salud, derechos de terceros)?
2. **Idoneidad:** ¿la medida sirve para ese fin?
3. **Necesidad:** ¿hay una medida menos restrictiva igual de eficaz?
4. **Proporcionalidad en sentido estricto:** ¿el beneficio compensa la afectación del derecho?

- Falla en finalidad o es claramente desproporcionada → la pregunta "¿falla el test?" es **sí**.
- Pasa la finalidad, pero la necesidad o la proporción dependen de cómo se implemente → **depende**.
- Pasa los cuatro pasos → **no**.

## Paso 4. Checklist: las preguntas guía

Cada pregunta se responde **sí**, **no**, **depende** (el efecto depende de la implementación o de un
reglamento) o **no aplica**. Las marcadas como **crítica** vuelven rojo el proyecto si la respuesta es sí.
La lista vive en [`ai/preguntas.py`](preguntas.py), que también aplica la regla del semáforo.

| Dimensión | Pregunta | ¿Crítica? |
|---|---|---|
| Personas afectadas | ¿Afecta a grupos en situación de vulnerabilidad (niñez, mujeres, pueblos indígenas y afroperuanos, personas con discapacidad, adultos mayores, personas LGTBI, migrantes, personas privadas de libertad, defensores de DDHH)? | No |
| Personas afectadas | ¿Quiénes ganan y quiénes pierden con la norma? (respuesta abierta) | — |
| Contenido del derecho | ¿Restringe, suspende o elimina un derecho reconocido? | No (activa el test) |
| Contenido del derecho | Si restringe un derecho, ¿falla el test de proporcionalidad? | **Sí** |
| Contenido del derecho | ¿Es regresiva: reduce un nivel de protección ya alcanzado? | **Sí** |
| Estándares | ¿Contradice la Constitución o la jurisprudencia del Tribunal Constitucional? | **Sí** |
| Estándares | ¿Contradice un tratado ratificado o la jurisprudencia de la Corte IDH, incluidas las sentencias contra el Perú? | **Sí** |
| Institucionalidad democrática | ¿Altera el equilibrio de poderes: concentra facultades, limita el control político o judicial, o permite que un poder elija o remueva a los integrantes de otro? | **Sí** |
| Institucionalidad democrática | ¿Cambia reglas electorales o de representación cerca de una elección, o a favor de quienes la aprueban? | **Sí** |
| Institucionalidad democrática | ¿Debilita la rendición de cuentas, la transparencia o la lucha contra la corrupción? | No |
| Espacio cívico y participación | ¿Restringe a la sociedad civil, las ONG, la cooperación internacional, la prensa o la protesta? | **Sí** |
| Espacio cívico y participación | ¿Requería consulta previa o participación ciudadana, y no la prevé? | **Sí** |
| Calidad de la norma | ¿Tiene efectos retroactivos desfavorables? | **Sí** |
| Implementación e impacto | ¿Crea gasto sin financiamiento o choca con la regla fiscal? | No |
| Implementación e impacto | ¿Tiene impacto ambiental sin evaluación (bosques, minería informal, áreas protegidas)? | No |

## Paso 5. Semáforo (regla fija, no la elige el modelo)

| Color | Regla |
|---|---|
| **Rojo** | Al menos una pregunta **crítica** respondida "sí" |
| **Amarillo** | Ninguna crítica en "sí", pero alguna pregunta de contexto en "sí" o alguna respuesta "depende" |
| **Verde** | Todo "no" o "no aplica" (incluye los proyectos que **amplían** derechos) |

"Falla el test de proporcionalidad" solo cuenta si el proyecto además restringe un derecho. "Afecta a grupos en
situación de vulnerabilidad" solo cuenta si el proyecto además restringe un derecho o es regresivo: un proyecto que
protege a la niñez o a las mujeres las afecta, pero para bien, y es verde. Ante la duda entre
"sí" y "no" en una pregunta crítica, responder **"depende"** y explicar de qué depende: así el proyecto queda
amarillo y no rojo.

## Instrumentos de referencia por derecho

| Derecho o estándar | Instrumentos |
|---|---|
| Igualdad y no discriminación | Constitución art. 2.2; CADH arts. 1.1 y 24; PIDCP art. 26; CEDAW |
| Libertad de expresión y prensa | Constitución art. 2.4; CADH art. 13; PIDCP art. 19 |
| Acceso a la información pública | Constitución art. 2.5; CADH art. 13 (caso Claude Reyes); Acuerdo de Escazú art. 5 |
| Debido proceso y tutela judicial | Constitución art. 139; CADH arts. 8 y 25; PIDCP art. 14 |
| Independencia judicial y separación de poderes | Constitución arts. 43, 139.2; CADH art. 8.1; Principios básicos de la ONU sobre la independencia de la judicatura |
| Derechos políticos y elecciones | Constitución arts. 31 y 35; CADH art. 23; PIDCP art. 25 |
| Asociación y sociedad civil | Constitución art. 2.13; CADH art. 16; Declaración de la ONU sobre defensores de DDHH |
| Protesta y reunión | Constitución art. 2.12; CADH art. 15; PIDCP art. 21 |
| Integridad, libertad personal y uso de la fuerza | Constitución art. 2.24; CADH arts. 5 y 7; Principios básicos de la ONU sobre el empleo de la fuerza |
| Pueblos indígenas y consulta previa | Convenio 169 de la OIT arts. 6 y 15; Ley 29785; DNUDPI |
| Derechos de las mujeres | CEDAW; Convención de Belém do Pará |
| Niñez y adolescencia | Convención sobre los Derechos del Niño (arts. 3, 37 y 40); CADH art. 19; Corte IDH OC-17/2002 |
| Ambiente sano | Constitución art. 2.22; Protocolo de San Salvador art. 11; Acuerdo de Escazú; Corte IDH OC-23/2017 |
| Salud y educación | PIDESC arts. 12 y 13; Constitución arts. 7, 13 y 16 |
| Derechos laborales y seguridad social | Constitución arts. 22-29; PIDESC arts. 6-9; convenios de la OIT |
| Corrupción y rendición de cuentas | Convención de la ONU contra la Corrupción; Convención Interamericana contra la Corrupción |
| Sostenibilidad fiscal | Constitución art. 79 (iniciativa de gasto); Decreto Legislativo 1276 (regla fiscal) |
| Amnistías y graves violaciones | CADH arts. 1.1, 8 y 25; Corte IDH, casos Barrios Altos (2001) y La Cantuta (2006) |

El Acuerdo de Escazú está firmado pero **no ratificado** por el Perú: sirve como referencia y no cuenta como
"tratado ratificado" en la pregunta de estándares. Situación y fuente oficial de cada instrumento:
[`docs/marco_legal.md`](../docs/marco_legal.md).

**Citar solo artículos que existan.** Si no hay certeza del número de artículo, citar solo el instrumento.

## Ejemplos

- **Rojo:** juzgar como adultos a adolescentes de 14 a 17 años (CDN arts. 37 y 40). Amnistiar delitos cometidos
  en protestas, incluidas muertes y lesiones (Barrios Altos). Ampliar a 15 días la detención policial sin control
  judicial (CADH art. 7.5).
- **Amarillo:** delegar facultades legislativas al Ejecutivo en materias amplias, incluida la penal (depende del
  alcance de los decretos). Crear un gasto sin fuente de financiamiento.
- **Verde:** negar licencias de armas a personas condenadas por tráfico de armas (regulación con finalidad
  legítima y proporcional). Restituir la interpretación conforme a la jurisprudencia de la Corte IDH. Declarar de
  interés nacional una obra.

## La cita textual

Copiar una frase **exacta** de la fórmula legal (10 a 40 palabras) que sustente la clasificación. Nunca un título
de sección ("EXPOSICIÓN DE MOTIVOS") ni texto inventado. Python verifica que la cita exista en el PDF.

*Es una alerta temprana para priorizar el trabajo, no una opinión legal.*
