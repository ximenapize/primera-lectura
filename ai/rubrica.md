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

- Falla en finalidad o es claramente desproporcionada → **rojo**.
- Pasa la finalidad, pero la necesidad o la proporción dependen de cómo se implemente → **amarillo**.
- Pasa los cuatro pasos → **verde**.

## Paso 4. Semáforo

| Color | Cuándo |
|---|---|
| **Rojo** | Retrocede claramente un derecho o un estándar de gobernanza, o falla el test de proporcionalidad |
| **Amarillo** | Toca un derecho o estándar y su efecto depende de la implementación; o tiene impacto fiscal sin financiamiento |
| **Verde** | No afecta derechos ni estándares de forma relevante, o los amplía |

Ante la duda entre rojo y amarillo: **amarillo**, explicando de qué depende.

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
