# Data Agents Research · Michael Jordan

**Pregunta de investigación.** ¿Puede un agente de datos ayudar a aficionados de la NBA y estudiantes a responder preguntas sobre la carrera de Michael Jordan, con resultados que puedan verificar por partido, temporada y fase?

| Caso de uso | Objetivo | Estado al 10 de noviembre de 2026 |
|---|---|---|
| Michael Jordan · Carrera NBA | Consultar puntos, tiros de dos, triples y actuaciones de doble dígito mediante preguntas en español, tablas y gráficas. | Prototipo construido y dataset verificado. Pruebas con participantes pendientes. |

## 1. Elección de tecnología emergente

Un agente de datos traduce una pregunta en lenguaje natural a una operación sobre una fuente definida y presenta el resultado con contexto suficiente para verificarlo. En este caso, el agente combina **un modelo de lenguaje local con salida estructurada, un motor de agregación y una interfaz conversacional**. Qwen interpreta la intención. llama.cpp ejecuta el modelo. Python valida el plan y calcula cada cifra a partir del registro por partido. La interfaz presenta el alcance, la cantidad de partidos analizados, una gráfica y una tabla.

El caso permite explorar preguntas que surgen durante el análisis, como limitar a playoffs una consulta previa sobre los triples de 1996-97. También permite observar errores de interpretación: «dobles» puede aludir tanto a tiros de dos como a dobles-dobles. [Ficha del modelo Qwen](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF), [documentación del servidor llama.cpp](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md), [glosario NBA](https://www.nba.com/stats/help/glossary)

## 2. Justificación de la oportunidad

Al investigar la carrera de Jordan es frecuente alternar entre totales, promedios y partidos individuales. Si la pregunta cambia de fase o temporada, el usuario debe reconocer qué filtros siguen vigentes. El prototipo reúne el resultado y su denominador en la misma vista. La hipótesis es que esta interacción facilita las consultas exploratorias y hace más visible cuándo el agente interpretó mal un filtro. Las pruebas de campo comprobarán esta hipótesis.

El benchmark BIRD propone 12,751 pares de preguntas y consultas sobre 95 bases de datos en 37 dominios. Sus autores destacan la necesidad de interpretar valores y contexto de la base de datos, además de la estructura de la consulta. Eso orientó la decisión de restringir el prototipo a un catálogo con métricas, equipos y rivales válidos. Los resultados de BIRD pertenecen a una tarea de texto a SQL con otro alcance. [Li et al., NeurIPS 2023](https://proceedings.neurips.cc/paper_files/paper/2023/hash/83fc8fab1710363050bbd1d4b8cc0021-Abstract-Datasets_and_Benchmarks.html)

Databricks Genie permite incorporar consultas verificadas y evaluar el comportamiento con preguntas de referencia. Este caso adapta dos prácticas: definir operaciones que calculan las cifras de manera reproducible y comprobar resultados conocidos. La publicación de un repositorio activo, versiones y documentación de servidor en llama.cpp, junto con modelos descargables de Qwen, permite reproducir la arquitectura y cambiar de modelo para comparar resultados. [Conceptos de Genie Agents](https://docs.databricks.com/aws/en/genie-agents/concepts), [versiones de llama.cpp](https://github.com/ggml-org/llama.cpp/releases), [repositorio de Qwen2.5](https://github.com/QwenLM/Qwen2.5)

El costo de extensión está en preparar datos y definir semántica por deporte, temporada y competición. Un esquema válido garantiza que la consulta se pueda ejecutar, pero el modelo aún puede elegir una métrica o un filtro distinto del que esperaba el usuario. Un equipo renombrado exige además decidir si el análisis se hará por nombre histórico o por franquicia. En equipos con menos memoria o CPU, la inferencia local puede aumentar la latencia.

## 3. Construcción del prototipo

1. **Datos.** Se descargó el CSV de Eoin A. Moore y se filtró el jugador NBA 893. La extracción dejó 1,251 partidos entre 1984 y 2003. El importador valida el conteo, la anotación, los triples y el récord de cada fase. El [diccionario de datos](../data/README.md) incluye la versión, las fuentes comparadas y las fórmulas.
2. **Interpretación.** Qwen recibe la pregunta y el plan anterior cuando detecta una continuación. Devuelve una operación, una métrica y filtros mediante un esquema JSON. Si la redacción se reconoce por reglas y los dos planes difieren, se utiliza el plan por reglas. La interfaz muestra qué interpretación se aplicó. El modo por reglas permite utilizar el mismo dataset sin cargar el modelo.
3. **Cálculo.** Python valida el catálogo y aplica filtros por temporada, fase, equipo o rival. Calcula totales, promedios, máximos, conteos por umbral y clasificaciones por partido. Los tiros de dos se derivan de los tiros de campo y triples convertidos. Los dobles-dobles y triples-dobles se calculan por categorías alcanzadas en cada partido.
4. **Visualización.** La interfaz muestra el alcance, la base de partidos, una gráfica de barras y una tabla ordenable. Conserva el contexto en preguntas de seguimiento. El prototipo corre localmente con Python y, en modo IA, con un servidor local de llama.cpp. El [README](../README.md) explica cómo ejecutar ambos modos.

## 4. Pruebas en campo

Se preparó un [protocolo de sesiones moderadas](pruebas-de-campo.md) con escenarios para comparar fases, conservar el contexto, aclarar «dobles» y localizar un partido. Incluye instrucciones para reclutar a personas del público objetivo, registrar consultas textuales, observar tiempos y ayudas, y preguntar por experiencia, mejoras y disposición a pagar. Las observaciones y respuestas se incorporarán con códigos anonimizados después de las sesiones.

## 5. Revisión de resultados

### Verificación técnica

| Comprobación | Resultado reproducido |
|---|---|
| Temporada regular | 1,072 partidos, 32,292 puntos, 30.12 puntos por partido, 581 triples anotados. |
| Playoffs | 179 partidos, 5,987 puntos, 33.45 puntos por partido, 148 triples anotados. |
| Máximos de anotación | 69 contra Cleveland el 28 de marzo de 1990 en regular y 63 contra Boston el 20 de abril de 1986 en playoffs. |
| Continuación de una consulta | 124 triples en 1996-97 al incluir ambas fases. «¿Y en playoffs?» mantiene la temporada y devuelve 13. |
| Umbrales | 38 partidos de playoffs con al menos 40 puntos. Con más de 40, el conteo baja a 35. |
| Ambigüedad y filtros vacíos | El modo por reglas pide aclarar «dobles». La combinación 1994-95 y Wizards devuelve cero partidos. |

Las comprobaciones de código se reproducen con `python -m unittest discover -s tests -v`. Una prueba en Chrome comprobó la gráfica, el orden de la tabla, el reinicio de contexto y la continuación de una pregunta. Se verificaron una vista de escritorio de 1,440 px y otra móvil de 390 px.

Los totales de partidos y puntos se contrastaron con los registros publicados por la NBA. Los máximos se verificaron con las crónicas oficiales. [Guía de medios de la NBA](https://cdn.nba.com/teams/uploads/sites/1610612740/2024/10/2024-25-Pelicans-Media-Guide-v2.pdf), [líderes NBA en playoffs](https://www.nba.com/stats/alltime-leaders?ActiveFlag=No&SeasonType=Playoffs), [69 puntos en regular](https://www.nba.com/news/legendary-moments-history-michael-jordan-69-points-vs-cleveland-cavs-1990), [63 en playoffs](https://www.nba.com/news/most-points-scored-nba-playoff-game)

### Resultados de campo e iteración

Pendientes hasta completar las sesiones. Para cada tarea se calculará la proporción completada sin ayuda y la mediana de tiempo, indicando el número de observaciones. También se registrarán las confusiones recurrentes de métrica y alcance y se resumirá la disposición a pagar como dato exploratorio de la muestra.

Si se repiten errores con los nombres históricos, se ampliará el catálogo de alias y se verificará el cambio con las preguntas observadas. Si se confunden tiros de dos con dobles-dobles, se probará una aclaración con opciones explícitas. Si los participantes pasan por alto la fase, se ensayarán filtros visibles junto al gráfico y se repetirá la tarea correspondiente.
