# Marco legal de la lectura

Con estas normas se lee cada proyecto de ley en el lente de **derechos humanos y gobernanza**. Es la misma lista
del cuadro "Instrumentos por derecho" de la rúbrica ([`ai/rubrica.md`](../ai/rubrica.md)), con su situación en el
Perú y un enlace a la fuente oficial.

## Cómo la usa la IA hoy

La IA **no descarga ni consulta estos textos**. Trabaja así:

- **Primera lectura (qwen2.5, local):** el prompt de [`ai/riesgo.py`](../ai/riesgo.py) le da solo los **nombres**
  de los instrumentos ("Constitución, CADH, PIDCP…"). El contenido de cada artículo lo trae de lo que aprendió en
  su entrenamiento, y por eso a veces cita un artículo equivocado.
- **Segunda lectura (Claude Sonnet, skill `revisando-alertas`):** lee la rúbrica completa, que dice qué
  instrumento y qué artículo corresponde a cada derecho (cuadro de abajo), y lo aplica con lo que sabe del
  derecho. La skill le pide citar el artículo solo si está seguro.
- **Lo que sí se verifica con Python:** la cita del **proyecto de ley** (que la frase exista en el PDF). La
  referencia a la norma (por ejemplo "CADH art. 7.5") todavía no se verifica contra el texto de la norma.

**Siguiente paso:** guardar en el repositorio el texto de los artículos clave de cada instrumento y pasárselos al
modelo según el derecho en juego (RAG). Así la IA lee el artículo del proyecto **y** el artículo de la norma, y la
referencia se puede verificar igual que la cita.

## Instrumentos

| Instrumento | Para qué derechos se usa | Situación en el Perú | Fuente oficial |
|---|---|---|---|
| Constitución Política del Perú (1993) | Todos: igualdad (2.2), expresión (2.4), información (2.5), reunión (2.12), asociación (2.13), ambiente (2.22), libertad personal (2.24), debido proceso (139), iniciativa de gasto (79) | Vigente | [gob.pe](https://www.gob.pe/institucion/presidencia/informes-publicaciones/196158-constitucion-politica-del-peru) · [TC, texto actualizado](https://www.tc.gob.pe/wp-content/uploads/2019/01/Constitucion-Politica-del-Peru-1993-actualizado-14.12.2020.pdf) |
| Convención Americana sobre Derechos Humanos (CADH) | Igualdad (1.1, 24), integridad y libertad personal (5, 7), debido proceso (8, 25), expresión e información (13), reunión (15), asociación (16), niñez (19), derechos políticos (23) | Ratificada | [OEA](https://www.oas.org/dil/esp/tratados_b-32_convencion_americana_sobre_derechos_humanos.htm) |
| Pacto Internacional de Derechos Civiles y Políticos (PIDCP) | Debido proceso (14), expresión (19), reunión (21), participación (25), igualdad (26) | Ratificado | [ONU](https://www.ohchr.org/es/instruments-mechanisms/instruments/international-covenant-civil-and-political-rights) |
| Pacto Internacional de Derechos Económicos, Sociales y Culturales (PIDESC) | Trabajo y seguridad social (6-9), salud (12), educación (13) | Ratificado | [ONU](https://www.ohchr.org/es/instruments-mechanisms/instruments/international-covenant-economic-social-and-cultural-rights) |
| Convención sobre los Derechos del Niño | Niñez y adolescencia (3, 37, 40) | Ratificada | [ONU](https://www.ohchr.org/es/instruments-mechanisms/instruments/convention-rights-child) |
| CEDAW | Derechos de las mujeres, igualdad | Ratificada | [ONU](https://www.ohchr.org/es/instruments-mechanisms/instruments/convention-elimination-all-forms-discrimination-against-women) |
| Convención de Belém do Pará | Violencia contra las mujeres | Ratificada | [OEA](https://www.oas.org/juridico/spanish/tratados/a-61.html) |
| Protocolo de San Salvador | Ambiente sano (11), derechos sociales | Ratificado | [OEA](https://www.oas.org/juridico/spanish/tratados/a-52.html) |
| Convenio 169 de la OIT | Pueblos indígenas y consulta previa (6, 15) | Ratificado | [OIT](https://normlex.ilo.org/dyn/nrmlx_es/f?p=NORMLEXPUB:12100:0::NO::P12100_ILO_CODE:C169) |
| Ley 29785, Ley del derecho a la consulta previa | Consulta previa | Vigente | [Congreso](https://leyes.congreso.gob.pe/Documentos/Leyes/29785.pdf) |
| Declaración de la ONU sobre los Derechos de los Pueblos Indígenas | Pueblos indígenas | Declaración (no es tratado) | [ONU](https://www.un.org/esa/socdev/unpfii/documents/DRIPS_es.pdf) |
| Acuerdo de Escazú | Acceso a la información ambiental (5), ambiente | **Firmado, no ratificado:** se usa como referencia, no como obligación | [CEPAL](https://www.cepal.org/es/acuerdodeescazu) |
| Convención de la ONU contra la Corrupción | Corrupción y rendición de cuentas | Ratificada | [UNODC](https://www.unodc.org/unodc/es/corruption/uncac.html) |
| Convención Interamericana contra la Corrupción | Corrupción y rendición de cuentas | Ratificada | [OEA](https://www.oas.org/juridico/spanish/tratados/b-58.html) |
| Decreto Legislativo 1276 (regla fiscal) | Sostenibilidad fiscal | Vigente | [Congreso](https://leyes.congreso.gob.pe/Documentos/DecretosLegislativos/01276.pdf) |
| Reglas Mandela (reglas mínimas para el tratamiento de los reclusos) | Personas privadas de libertad | Estándar de la ONU (no es tratado) | [UNODC](https://www.unodc.org/documents/justice-and-prison-reform/Nelson_Mandela_Rules-S-ebook.pdf) |
| Principios básicos sobre el empleo de la fuerza y armas de fuego | Uso de la fuerza | Estándar de la ONU (no es tratado) | [ONU](https://www.ohchr.org/es/instruments-mechanisms/instruments/basic-principles-use-force-and-firearms-law-enforcement-officials) |
| Principios básicos relativos a la independencia de la judicatura | Independencia judicial | Estándar de la ONU (no es tratado) | [ONU](https://www.ohchr.org/es/instruments-mechanisms/instruments/basic-principles-independence-judiciary) |
| Declaración de la ONU sobre defensores de derechos humanos | Sociedad civil y defensores | Declaración (no es tratado) | [ONU](https://www.ohchr.org/es/instruments-mechanisms/instruments/declaration-right-and-responsibility-individuals-groups-and) |
| Corte IDH, casos Barrios Altos (2001) y La Cantuta (2006) | Amnistías y graves violaciones | Sentencias contra el Perú, obligatorias | [Barrios Altos](https://www.corteidh.or.cr/docs/casos/articulos/Seriec_75_esp.pdf) · [La Cantuta](https://www.corteidh.or.cr/docs/casos/articulos/seriec_162_esp.pdf) |
| Corte IDH, caso Claude Reyes (2006) | Acceso a la información | Precedente interamericano | [Sentencia](https://www.corteidh.or.cr/docs/casos/articulos/seriec_151_esp.pdf) |
| Corte IDH, Opiniones Consultivas 17/2002 y 23/2017 | Niñez (OC-17) y ambiente (OC-23) | Guía de interpretación de la CADH | [OC-17](https://www.corteidh.or.cr/docs/opiniones/seriea_17_esp.pdf) · [OC-23](https://www.corteidh.or.cr/docs/opiniones/seriea_23_esp.pdf) |

*La lectura es una alerta temprana para priorizar el trabajo, no una opinión legal.*
