# Datos y reproducibilidad

## Fuentes verificadas

| Fuente | Cobertura comprobada o declarada | Uso |
|---|---|---|
| [Eoin A. Moore · NBA Dataset: Box Scores and Stats, v543](https://www.kaggle.com/datasets/eoinamoore/historical-nba-data-and-player-box-scores/versions/543) | Se verificó el archivo `PlayerStatistics.csv` y se extrajeron los 1,251 partidos de Jordan. El catálogo de la versión consultada declara CC0. | Fuente operativa. [Pipeline publicado por el autor](https://github.com/eoinmooremath/nba-data-pipeline) |
| [NBA Stats · Michael Jordan](https://www.nba.com/stats/player/893/traditional) | Perfil oficial con temporadas y estadísticas tradicionales. La [guía de medios](https://cdn.nba.com/teams/uploads/sites/1610612740/2024/10/2024-25-Pelicans-Media-Guide-v2.pdf) confirma partidos y puntos de regular. La tabla de [playoffs](https://www.nba.com/stats/alltime-leaders?ActiveFlag=No&SeasonType=Playoffs) confirma partidos, puntos y triples de esa fase. | Referencia para los controles de integridad. |
| [Basketball-Reference](https://www.basketball-reference.com/players/j/jordami01.html) y [Stathead](https://www.sports-reference.com/stathead/basketball/player-game-finder.cgi?player_id=jordami01) | Totales por temporada y buscador histórico por partido. | Contraste adicional, incluido el total de 581 triples en regular, y consulta manual. |
| [Maven Analytics · Jordan & LeBron Career Stats](https://mavenanalytics.io/data-playground/jordan-lebron-career-stats) | La ficha describe un CSV por partido de Jordan y LeBron con regular y playoffs. La descarga solicita iniciar sesión y la ficha declara GPL 2. Se revisó la ficha. | Alternativa para una comparación entre jugadores. |
| [NBA Historical Datasets 1996–2026](https://github.com/dckp1000/NBA-96-26-DATASET) | El autor indica que la cobertura de jugadas y tiros de NBA Stats comienza en 1996-97. | Posible complemento para estudiar localización de tiros en temporadas tardías. |

## Extracción

`jordan.csv` conserva una fila por partido disputado por el jugador NBA **893**, del 26 de octubre de 1984 al 16 de abril de 2003. Comprende 15 temporadas y dos equipos. Se excluyeron siete registros de All-Star presentes en el archivo de origen y dos filas de temporada regular sin minutos.

1. Descarga la versión 543 desde la ficha de Kaggle y extrae `PlayerStatistics.csv`. El archivo verificado tenía **391,267,105 bytes**.
2. Desde la raíz ejecuta `python importar.py /ruta/PlayerStatistics.csv`.
3. Ejecuta `python -m unittest discover -s tests -v`.

SHA-256 de `PlayerStatistics.csv`:

```text
b9a22c1546ac2924363488f3d8892af8ff8a89f0a942638a08be39f1d9429676
```

SHA-256 de `jordan.csv` con finales de línea LF:

```text
86173113cf834d31ba1308fb9175b6b8d13d56d762f1439a01b5c7e7169b34fc
```

## Diccionario

| Campo | Definición |
|---|---|
| `id`, `fecha`, `temporada` | ID NBA de diez caracteres, fecha del juego de la fuente y temporada de inicio a fin. |
| `fase`, `equipo`, `rival` | Regular o Playoffs, equipo de Jordan y nombre histórico del oponente. |
| `local`, `victoria`, `min` | Indicadores 0/1 de localía y victoria y minutos jugados. |
| `pts`, `fgm`, `fga` | Puntos y tiros de campo convertidos e intentados. |
| `3pm`, `3pa`, `ftm`, `fta` | Triples y tiros libres, convertidos e intentados. |
| `reb`, `ast`, `stl`, `blk` | Rebotes totales, asistencias, robos y tapones. |
| `2pm` | Se calcula como `fgm − 3pm`. |
| `dd`, `td` | Se calculan por partido. Exactamente dos, o tres o más, categorías con diez o más entre PTS, REB, AST, STL y BLK. |

El importador valida IDs únicos, correspondencia de temporada con el ID NBA, campos numéricos no negativos, coherencia básica de tiros y la identidad `PTS = 2 × FGM + 3PM + FTM` en cada partido. También verifica partidos, puntos, triples y récord por fase. La NBA documenta [los 69 puntos ante Cleveland](https://www.nba.com/news/legendary-moments-history-michael-jordan-69-points-vs-cleveland-cavs-1990) y [los 63 ante Boston en playoffs](https://www.nba.com/news/most-points-scored-nba-playoff-game).

La unidad de análisis es el partido. El CSV no contiene coordenadas de tiro ni secuencias de posesiones. Los oponentes conservan su denominación histórica, por lo que, por ejemplo, Washington Bullets y Washington Wizards aparecen como rivales distintos. Las comprobaciones de integridad detectan inconsistencias y contrastan agregados. No se hizo un cotejo manual de cada celda con cada box score oficial.
