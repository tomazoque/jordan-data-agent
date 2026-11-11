# Michael Jordan · Data Agents Research

Caso académico sobre el uso de un agente de datos para explorar la carrera NBA de Michael Jordan. El prototipo responde preguntas en español y presenta cada resultado con su alcance, una gráfica de barras y una tabla ordenable.

| Fase NBA | Partidos | Puntos | Tiros de dos anotados | Triples anotados | Dobles-dobles | Triples-dobles |
|---|---:|---:|---:|---:|---:|---:|
| Temporada regular | 1,072 | 32,292 | 11,611 | 581 | 172 | 28 |
| Playoffs | 179 | 5,987 | 2,040 | 148 | 37 | 2 |

Los dobles-dobles cuentan exactamente dos categorías con al menos diez y los triples-dobles, tres o más. Las categorías son puntos, rebotes, asistencias, robos y tapones. La tabla separa ambos eventos para que cada partido pertenezca como máximo a una categoría. [Glosario NBA](https://www.nba.com/stats/help/glossary)

## Abrir el prototipo

Con Python 3.10 o posterior, ejecuta desde la raíz del repositorio:

```bash
python app.py
```

Abre [el prototipo local](http://127.0.0.1:8765). El modo por reglas funciona con los datos incluidos y la biblioteca estándar de Python. Prueba «¿Cuántos triples anotó en 1996-97?» y continúa con «¿Y en playoffs?». Puedes iniciar una consulta independiente con **Nueva consulta**.

### Ejecutar con IA local

Descarga una distribución de [llama.cpp](https://github.com/ggml-org/llama.cpp/releases) para tu sistema y el archivo `qwen2.5-1.5b-instruct-q4_k_m.gguf` del [repositorio de Qwen](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF). El modelo ocupa aproximadamente 1.12 GB.

En una terminal, ejecuta `llama-server` desde su carpeta o con su ruta completa. En PowerShell, usa `./llama-server.exe` si el ejecutable está en la carpeta actual.

```bash
llama-server -m /ruta/al/modelo.gguf --alias qwen-jordan --host 127.0.0.1 --port 8081 -c 4096
```

En otra terminal, inicia el prototipo desde el repositorio. Usa otro puerto si el modo por reglas está abierto.

```bash
python app.py --modelo qwen-jordan --puerto 8766
```

Abre [el modo con IA](http://127.0.0.1:8766). El modelo propone un plan estructurado y el motor calcula la respuesta sobre el CSV. Si la pregunta tiene una interpretación explícita por reglas y los planes difieren, el prototipo usa las reglas de control. **Cómo se calculó** muestra qué interpretación se aplicó. Revisa el alcance y la base de partidos de cada respuesta.

## Investigación y datos

- [Informe académico de cinco fases](docs/investigacion.md)
- [Protocolo y ficha de pruebas de campo](docs/pruebas-de-campo.md)
- [Origen, diccionario y validación del dataset](data/README.md)

Para ejecutar las comprobaciones automatizadas:

```bash
python -m unittest discover -s tests -v
```
