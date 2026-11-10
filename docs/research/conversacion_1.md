# Conversación 1: responsable de tecnología de un observatorio legislativo

- **Con quién:** subcoordinador de desarrollo y tecnología de un observatorio ciudadano de la sociedad civil
  enfocado en el trabajo legislativo del Congreso del Perú (ejes: medio ambiente, democracia, institucionalidad,
  derechos humanos).
- **Medio:** conversación grabada (unos 12 minutos), con su permiso.
- **Anonimización:** se omiten nombres de personas e instituciones. El audio se transcribió en local con Whisper
  large-v3-turbo y no se sube al repositorio. La transcripción está editada para quitar muletillas y repeticiones,
  sin cambiar el contenido.

---

## La conversación

**Ximena:** ¿Me podrías contar un poco sobre el trabajo que hacen en el observatorio?

**Entrevistado:** Tengo el rol de subcoordinador de desarrollo y tecnología. Somos un observatorio ciudadano
enfocado en el tema legislativo: miramos proyectos de ley que vienen arrastrándose desde gestiones anteriores o que
salen ahora y que estarían atentando contra ejes clave que consideramos, como medio ambiente, democracia e
institucionalidad. Tratamos de acercar esa información a la ciudadanía de una manera amigable, rápida y veraz.

**Ximena:** Para ver todo el trabajo legislativo, ¿cómo ven qué proyecto de ley se ha publicado cada día? ¿Van al
portal todos los días o tienen alguna herramienta automatizada?

**Entrevistado:** Tenemos una herramienta automatizada que corre una vez cada semana. Es un scrapeo general de la
página de proposiciones legislativas, tanto de la Cámara de Diputados como del Senado, y revisa todo. Ahora hay, por
ejemplo, unos 400 proyectos de ley y la próxima semana habrá unos 20 más. Lo que hacemos es revisar nuevamente desde
el primero hasta el último. ¿Por qué? Porque no hay un orden secuencial en la modificación de los proyectos: la
numeración es según cómo se presentan. El proyecto número 2 puede pasar a comisión o ir a votación, o el número 200
puede estar aprobándose. Entonces conviene revisar todo de manera holística para ver cuáles son los cambios. Y esos
cambios los ve un equipo.

**Ximena:** ¿No hay algo que haga el seguimiento de cómo va avanzando una ley?

**Entrevistado:** Es un trabajo mixto. El scrapeo recoge cada cambio como una fila: "el proyecto 1 pasó esto", y se
agrega una nueva fila cuando pasa otra cosa. Adicionalmente tenemos una herramienta con un LLM que compara una
versión del Excel (o de la base de datos) de proyectos de ley con la otra y verifica cuáles son los cambios.
Naturalmente no nos interesan todos los cambios, porque tenemos nuestros ejes delimitados; se lo aplicamos a los que
pasan un primer filtro.

**Ximena:** ¿Cómo identifican que cada ley pertenece a uno de esos ejes temáticos?

**Entrevistado:** También con el LLM: una lectura preliminar de las **sumillas**. Por temas de recursos, tratamos de
minimizar el uso de IA por el costo que tiene, y por eso se aplica solo sobre las sumillas. Esto puede generar que
algo que está en el cuerpo del proyecto de ley, pero no en la sumilla, se nos pase. Por ejemplo, cuando se presentó
el proyecto para volver a las dos cámaras, el impacto real que tendría (en las votaciones, en la cuestión de
confianza, etc.) estaba en el cuerpo; no se podía deducir de la sumilla.

**Ximena:** ¿Y los sistemas de alerta, cuando un proyecto de ley puede atentar o no contra algún eje, los ven
ustedes u otra comisión? ¿Cómo identifican que un proyecto es riesgoso?

**Entrevistado:** Hay un trabajo paralelo. Una comisión de seguimiento revisa diariamente, pero con criterios
generales. Y aparte hay una comisión de análisis, donde trabaja alguien de ciencias sociales de la mano con un
abogado o estudiante de derecho; gente que está terminando su formación universitaria o ya es profesional. Es un
enfoque complementario: revisar **uno por uno**. Eso limita la velocidad con la que se pueden hacer los análisis.

Donde entra mi comisión es en hacer un primer mapeo general, reconociendo que hay un margen de error, un margen de
alucinación, sobre todo porque no usamos modelos muy sofisticados. No usamos Claude ni OpenAI: estamos limitados a
Gemini, porque tenía un plan accesible. Señala "esto podría ser interesante", con la posibilidad de falsos positivos
y falsos negativos. Las comisiones también se nutren de lo que pasa alrededor: comentarios en sus espacios
profesionales, redes sociales, noticias, medios independientes u otros observatorios que señalan algo como
importante.

**Ximena:** En todo el flujo, desde que scrapean los proyectos, los clasifican por sus sumillas, hasta el producto
final (los posts en redes o los análisis en su página), ¿cuál es el paso que más tiempo les toma?

**Entrevistado:** Creería que todo el tema de **seguimiento**. Hacer los análisis toma tiempo, pero es algo que hemos
estudiado y trabajado: tenemos el know-how. Lo que nos haría la vida más fácil es tener un **seguimiento constante de
los cambios y de lo que implican**, no solo de manera cuantitativa sino cualitativa. No es complicado, pero toma un
montón de tiempo estar revisando, sobre todo porque **no existe una periodicidad** de los eventos. Tendríamos que
tener a alguien siempre conectado; lo que hacemos es una periodicidad un poco arbitraria: "el miércoles le funciona a
todos, hagámoslo el miércoles", pero no es necesariamente la mejor alternativa. Pueden pasar cosas en otros
momentos, y eso requiere que alguien esté revisando, pendiente de las cosas. O, si no alguien, **algo**.

**Ximena:** Creo que eso sería todo. ¡Gracias por tu tiempo!

**Entrevistado:** Cuando quieras.

---

## Resumen para el README

| | Lo que dijo |
|---|---|
| **Cómo lo resuelven hoy** | Scraper propio que corre **una vez por semana** y vuelve a revisar los ~400 proyectos, porque los cambios no son secuenciales. Un LLM compara versiones del Excel para detectar cambios |
| **Clasificación** | Un LLM (Gemini, por costo) lee **solo la sumilla**; lo que está en el cuerpo del proyecto se puede pasar |
| **Alertas de riesgo** | Comisión de seguimiento (criterios generales) + comisión de análisis (ciencias sociales + derecho) que revisa **uno por uno**: es lento |
| **Qué les cuesta más** | El **seguimiento constante** de cambios y de lo que implican; no hay periodicidad, así que revisan un día arbitrario de la semana |
| **Límites de la IA que usan** | Modelo barato, con alucinaciones, falsos positivos y falsos negativos |

**Frases para el pitch:**
- *"Tratamos de minimizar el uso de IA por el costo que esto tiene, y se aplica sobre las sumillas."*
- *"Algo que está en el cuerpo del proyecto, pero no en la sumilla, se nos pase."*
- *"Revisar uno por uno naturalmente limita la velocidad."*
- *"Requiere que alguien esté revisando, pendiente de las cosas. O, si no alguien, algo."*

## Qué cambió en el producto después de hablar
1. **Leer el cuerpo del proyecto, no solo la sumilla:** Primera Lectura lee la fórmula legal del PDF. Con un modelo
   abierto en local, el costo marginal es casi cero, que es justo la barrera que les impide leer más allá de la
   sumilla.
2. **Seguimiento diario, no semanal:** el scraper corre todos los días y guarda cada movimiento.
3. **Cita textual verificada:** responde a su preocupación por las alucinaciones; si el modelo cita algo que no
   está en el PDF, se marca.
4. **Segunda lectura solo de las alertas:** el agente revisor reduce los falsos positivos sin revisar uno por uno.
5. **Competencia:** el observatorio ya tiene scraper y un LLM barato sobre sumillas. Primera Lectura se diferencia
   en leer el articulado, citar, verificar y conectar con las votaciones.
