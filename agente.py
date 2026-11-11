"""Interpreta preguntas y calcula estadísticas sobre un CSV local."""

import csv
import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path
from statistics import mean
from urllib.request import ProxyHandler, Request, build_opener


METRICS = {
    "pts": ("Puntos", r"puntos?|anotacion|ppg|pts"),
    "3pm": ("Triples anotados", r"triples?|tiros? de (?:3|tres)(?: puntos?)?|3pm"),
    "3pa": ("Triples intentados", r"(?:triples?|tiros? de (?:3|tres)(?: puntos?)?) intentados?|intentos? de triple|3pa"),
    "2pm": ("Tiros de dos anotados", r"tiros? de (?:2|dos)(?: puntos?)?|canastas? de (?:2|dos)(?: puntos?)?|2pm"),
    "dd": ("Dobles-dobles", r"dobles?[ -]dobles?|double[ -]doubles?"),
    "td": ("Triples-dobles", r"triples?[ -]dobles?|triple[ -]doubles?"),
    "reb": ("Rebotes", r"rebotes?|reb"),
    "ast": ("Asistencias", r"asistencias?|ast"),
    "stl": ("Robos", r"robos?|stl"),
    "blk": ("Tapones", r"tapones?|tapon|bloqueos?|blk"),
    "min": ("Minutos", r"minutos?"),
    "ftm": ("Tiros libres anotados", r"tiros? libres?|ftm"),
    "fgm": ("Tiros de campo anotados", r"tiros? de campo|fgm"),
    "victoria": ("Victorias", r"victorias?|gano"),
    "pj": ("Partidos", r"partidos? jugados?|juegos? jugados?|pj"),
}
GROUPS = {
    "temporada": ("Temporada", r"temporadas?"),
    "fase": ("Fase", r"fases?|tipos? de partido"),
    "equipo": ("Equipo", r"equipos?"),
    "rival": ("Rival", r"rivales?|oponentes?"),
}
FILTERS = ("fase", "temporada", "equipo", "rival")
DEFAULT = dict(operacion="total", metrica="pts", grupo="", fase="", temporada="",
               equipo="", rival="", limite=10, umbral=-1)


def display_number(value):
    return f"{value:,.2f}".rstrip("0").rstrip(".")


def normalize(text):
    return "".join(c for c in unicodedata.normalize("NFD", text.casefold())
                   if not unicodedata.combining(c))


def load_games(path=Path(__file__).with_name("data") / "jordan.csv"):
    with path.open(encoding="utf-8", newline="") as source:
        rows = list(csv.DictReader(source))
    for row in rows:
        for field in ("pts", "fgm", "fga", "3pm", "3pa", "ftm", "fta", "reb", "ast",
                      "stl", "blk", "victoria", "local"):
            row[field] = int(row[field])
        row["min"] = float(row["min"])
        row["2pm"] = row["fgm"] - row["3pm"]
        categories = sum(row[field] >= 10 for field in ("pts", "reb", "ast", "stl", "blk"))
        row["dd"] = int(categories == 2)
        row["td"] = int(categories >= 3)
        row["pj"] = 1
    return rows


class Agent:
    def __init__(self, games, model=None):
        self.games = games
        self.model = model
        self.options = {key: sorted({r[key] for r in games}) for key in FILTERS}
        self.properties = {
            "operacion": {"enum": ["total", "promedio", "maximo", "partidos", "ayuda"]},
            "metrica": {"enum": list(METRICS)},
            "grupo": {"enum": ["", *GROUPS]},
            **{k: {"enum": ["", *v]} for k, v in self.options.items()},
            "limite": {"type": "integer", "minimum": 1, "maximum": 100},
            "umbral": {"type": "integer", "minimum": -1, "maximum": 999},
        }

    def validate(self, plan):
        if not isinstance(plan, dict) or plan.keys() != self.properties.keys():
            raise ValueError("Consulta incompleta.")
        for field, spec in self.properties.items():
            value = plan[field]
            if "enum" in spec:
                valid = isinstance(value, str) and value in spec["enum"]
            else:
                valid = type(value) is int and spec["minimum"] <= value <= spec["maximum"]
            if not valid:
                raise ValueError(f"Valor fuera del catálogo: {field}.")
        if plan["grupo"] and plan["operacion"] == "partidos":
            raise ValueError("Agrupar solo está disponible para totales, promedios y máximos.")
        return plan

    def interpret(self, question, previous):
        q = normalize(question).lstrip("¿¡ ")
        if re.search(r"\b(dobles?|triples?)\b", q) and not re.search(
            r"\b(?:dobles?[ -]dobles?|triples?[ -]dobles?|double[ -]doubles?)\b", q
        ) and re.search(r"\bdobles?\b", q):
            raise ValueError("¿Te refieres a tiros de dos puntos o a dobles-dobles?")
        if re.search(r"\b(futbol|beisbol|all[ -]star|pretemporada|finales|porcentaje|eficiencia|predecir|prediccion|ubicacion|localia|local|visitante|racha|derrotas|perdidas|kobe|lebron|olimpicos)\b", q):
            raise ValueError("Puedes consultar el registro de Jordan por temporada, fase, equipo o rival.")

        if not self.model:
            return self.validate(self.rule_plan(q, previous)), "reglas"

        try:
            baseline = self.validate(self.rule_plan(q, previous))
        except ValueError:
            baseline = None
        if not re.match(r"^(?:y\b|ahora\b|solo\b|unicamente\b)", q):
            previous = None
        try:
            model_plan = self.model_plan(question, previous)
        except (ValueError, KeyError, IndexError, TypeError):
            if baseline is None:
                raise
            return baseline, "reglas de control"
        if baseline is not None and model_plan != baseline:
            return baseline, "reglas de control"
        return model_plan, "llama.cpp"

    def rule_plan(self, q, previous):
        follow_up = bool(previous and re.match(r"^(?:y\b|ahora\b|solo\b|unicamente\b)", q))
        plan = dict(previous if follow_up else DEFAULT)
        query_metrics = {}
        rest = q
        for key in ("td", "dd", "2pm", "3pa", "3pm", "pts", "reb", "ast", "stl",
                    "blk", "min", "ftm", "fgm", "victoria", "pj"):
            pattern = rf"\b(?:{METRICS[key][1]})\b"
            if re.search(pattern, rest):
                query_metrics[key] = True
                rest = re.sub(pattern, " ", rest)
        if len(query_metrics) > 1:
            raise ValueError("Selecciona una métrica por consulta.")
        if query_metrics:
            plan["metrica"] = next(iter(query_metrics))
            plan["umbral"] = -1
        if (re.search(r"\b(top|lista|muestra|dame|ensename|que partidos|cuales|mejores)\b", q)
                and re.search(r"\b(partidos|juegos|encuentros|actuaciones|top|lista)\b", q)):
            plan["operacion"], plan["grupo"] = "partidos", ""
        elif re.search(r"\b(maximo|record|mas puntos en un partido)\b", q):
            plan["operacion"] = "maximo"
        elif re.search(r"\b(promedio|media|promedia|ppg)\b|por partido\b", q):
            plan["operacion"] = "promedio"
        elif re.search(r"\bmayor\b", q):
            plan["operacion"] = "maximo"
        elif re.search(r"\b(total|totales|cuant[oa]s?|suma)\b", q):
            plan["operacion"] = "total"

        if re.search(r"\b(cuantos|numero de|cantidad de) (?:partidos|juegos)\b", q):
            threshold = re.search(r"(?:al menos|como minimo|mas de|con)\s+(\d{1,3})(?:\s*\+)?", q)
            if threshold:
                if not query_metrics and not follow_up:
                    raise ValueError("Indica qué estadística debe alcanzar ese mínimo.")
                plan["umbral"] = int(threshold[1]) + int(threshold[0].startswith("mas de"))
            elif not query_metrics:
                plan["metrica"] = "pj"
            elif plan["metrica"] not in {"dd", "td", "victoria", "pj"}:
                raise ValueError("Indica el mínimo de la estadística, por ejemplo «con al menos 40 puntos».")
        top = re.search(r"\b(?:top|(?:los|las))\s+(\d{1,3})\b", q)
        if top and plan["operacion"] == "partidos":
            plan["limite"] = int(top[1])

        for key, (_, pattern) in GROUPS.items():
            if re.search(rf"\b(?:por|cada) (?:{pattern})\b", q):
                plan["grupo"] = key
        playoffs = bool(re.search(r"\b(playoffs?|postemporada)\b", q))
        regular = bool(re.search(r"\b(regular|regulares)\b", q))
        if playoffs and regular:
            plan.update(fase="", grupo="fase")
        elif playoffs or regular:
            plan["fase"] = "Playoffs" if playoffs else "Regular"
            if plan["grupo"] == "fase":
                plan["grupo"] = ""
        if re.search(r"\b(ambas fases|toda la carrera)\b", q):
            for field in FILTERS:
                plan[field] = ""
        for value in self.options["equipo"]:
            if re.search(rf"\b{normalize(value)}\b", q):
                plan["equipo"] = value
        rivals = {normalize(value): value for value in self.options["rival"]}
        aliases = defaultdict(list)
        for name, value in rivals.items():
            city, nickname = name.rsplit(" ", 1)
            aliases[city].append(value)
            aliases[nickname].append(value)
        rival_match = re.search(r"\b(?:contra|frente a|vs\.?)\s+(?:los |las )?(.+)", q)
        if rival_match:
            for name, value in sorted(rivals.items(), key=lambda item: -len(item[0])):
                if re.match(rf"{re.escape(name)}\b", rival_match[1]):
                    plan["rival"] = value
                    break
            else:
                choices = next((aliases[name] for name in sorted(aliases, key=len, reverse=True)
                                if re.match(rf"{re.escape(name)}\b", rival_match[1])), [])
                if len(choices) != 1:
                    raise ValueError("Indica el nombre completo del rival, por ejemplo Boston Celtics.")
                plan["rival"] = choices[0]
            if plan["equipo"] and normalize(plan["equipo"]) in normalize(plan["rival"]):
                plan["equipo"] = ""
        if "bulls" in q and "wizards" in q and not rival_match:
            plan.update(equipo="", grupo="equipo")
        if (not rival_match and re.search(r"\b(compara|comparar|comparacion)\b", q)
                and not plan["grupo"]):
            raise ValueError("Indica los grupos que quieres comparar, por ejemplo regular y playoffs.")

        seasons = re.findall(r"\b((?:19|20)\d{2})[-–/](\d{4}|\d{2})\b", q)
        if len(seasons) > 1:
            raise ValueError("Usa una temporada por consulta o agrupa por temporada.")
        if seasons:
            start, end = seasons[0]
            if int(end) != ((int(start) + 1) if len(end) == 4 else (int(start) + 1) % 100):
                raise ValueError("Escribe la temporada como 1986-87.")
            plan["temporada"] = f"{start}-{end[-2:]}"
        elif re.search(r"\b(?:19|20)\d{2}\b", q):
            raise ValueError("Indica la temporada completa, por ejemplo 1997-98.")
        if not (query_metrics or follow_up or plan["operacion"] == "partidos"
                or plan["metrica"] == "pj"):
            raise ValueError("Indica una estadística, por ejemplo puntos, rebotes o triples-dobles.")
        if plan["umbral"] >= 0 and plan["operacion"] != "total":
            raise ValueError("El umbral se aplica al conteo de partidos.")
        return plan

    def model_plan(self, question, previous):
        schema = {"type": "object", "properties": self.properties,
                  "required": list(self.properties), "additionalProperties": False}
        system = (
            "Convierte la pregunta de baloncesto sobre Michael Jordan en un plan JSON. "
            "Empieza con estos valores predeterminados y cambia solo lo solicitado: "
            f"{json.dumps(DEFAULT)}. "
            "Operaciones: total suma, promedio calcula por partido, maximo da el récord, "
            "partidos muestra un top de encuentros, ayuda pide aclaración. "
            "Métricas: pts=puntos, pj=partidos, reb=rebotes, ast=asistencias, stl=robos, "
            "blk=tapones, dd=dobles-dobles, td=triples-dobles, "
            "3pm=triples anotados, 3pa=triples intentados, 2pm=tiros de dos anotados. "
            "Para contar partidos con al menos N de una métrica usa total y umbral=N. "
            "Usa el plan anterior únicamente en una continuación (por ejemplo '¿Y en playoffs?'). "
            "Deja fase, temporada, equipo y rival como cadenas vacías si no se solicitan. "
            "Un equipo es Bulls o Wizards. Para un rival usa el nombre completo histórico. "
            "Si comparan Regular y Playoffs, usa grupo='fase' y fase vacía. "
            "Las temporadas tienen formato AAAA-AA. Para un top usa grupo vacío y límite N. "
            "Ejemplos de campos que cambian respecto al predeterminado: "
            "'Cuantos triples anoto' -> metrica=3pm; "
            "'Compara el promedio de puntos en regular y playoffs' -> operacion=promedio, grupo=fase; "
            "'Producción anotadora habitual en cada campaña' -> operacion=promedio, grupo=temporada; "
            "'Top 3 por rebotes frente a los Celtics' -> operacion=partidos, metrica=reb, "
            "rival=Boston Celtics, limite=3; "
            "'Cuántos dobles-dobles en temporada regular' -> metrica=dd, fase=Regular. "
            "Selecciona ayuda para preguntas fuera de este dominio o ambiguas. "
            "Devuelve solo el objeto JSON con las nueve claves. La pregunta actual tiene prioridad."
        )
        body = {"model": self.model, "response_format": {"type": "json_schema", "schema": schema},
                "stream": False, "temperature": 0, "max_tokens": 384,
                "messages": [{"role": "system", "content": system},
                             {"role": "user", "content": json.dumps(
                                 {"pregunta": question, "plan_anterior": previous}, ensure_ascii=False)}]}
        request = Request("http://127.0.0.1:8081/v1/chat/completions", json.dumps(body).encode(),
                          {"Content-Type": "application/json"})
        with build_opener(ProxyHandler({})).open(request, timeout=90) as response:
            answer = json.load(response)
        return self.validate(json.loads(answer["choices"][0]["message"]["content"]))

    def answer(self, question, previous=None):
        plan, mode = self.interpret(question, self.validate(previous) if previous else None)
        operation, metric, group = (plan[k] for k in ("operacion", "metrica", "grupo"))
        if operation == "ayuda":
            raise ValueError("Reformula con una métrica y, si aplica, una temporada, fase, equipo o rival.")
        filters = {k: plan[k] for k in FILTERS if plan[k]}
        filtered = [r for r in self.games if all(r[k] == value for k, value in filters.items())]
        label = METRICS[metric][0]
        threshold = plan["umbral"]
        if threshold >= 0 and operation != "total":
            raise ValueError("El umbral se aplica al conteo de partidos.")

        def aggregate(rows):
            values = [r[metric] for r in rows]
            if threshold >= 0:
                return sum(value >= threshold for value in values)
            return round({"total": sum, "promedio": mean, "maximo": max}[operation](values), 2)

        title = f"Partidos con {threshold}+ · {label}" if threshold >= 0 else label
        if operation in {"promedio", "maximo"}:
            title = f"{label} · {operation.replace('maximo', 'máximo')} por partido"
        scope = " · ".join(filters.values()) or "Carrera NBA · regular y playoffs"
        if not filtered:
            return dict(plan=plan, modo=mode, titulo=title, alcance=scope, base=0,
                        mensaje="No hay partidos que coincidan con los filtros.", filas=[],
                        columnas=[], grafica=[])
        chart = []
        if operation == "partidos":
            selected = sorted(filtered, key=lambda r: (-r[metric], r["fecha"]))[:plan["limite"]]
            columns = ["Fecha", "Temporada", "Fase", "Equipo", "Rival", label, "Puntos"]
            if metric == "pts":
                columns.pop()
            rows = [[r["fecha"], r["temporada"], r["fase"], r["equipo"], r["rival"], r[metric]]
                    + ([r["pts"]] if metric != "pts" else []) for r in selected]
            chart = [[r["fecha"], r[metric]] for r in selected]
            message = f"{len(selected)} de {len(filtered)} partidos, ordenados por {label.lower()}."
        else:
            grouped = defaultdict(list)
            for row in filtered:
                grouped[row[group] if group else row["fase"]].append(row)
            rows = [[name, aggregate(items), len(items)] for name, items in sorted(grouped.items())]
            if group in {"", "fase"}:
                rows.sort(key=lambda row: row[0] != "Regular")
            if group == "rival":
                rows.sort(key=lambda row: (-row[1], row[0]))
            columns = [GROUPS[group or "fase"][0], title, "Partidos analizados"]
            chart = [row[:2] for row in rows]
            value = aggregate(filtered)
            if not group:
                message = f"{display_number(value)} · {title}"
            elif len(rows) <= 4:
                comparison = " · ".join(f"{name} {display_number(amount)}" for name, amount, _ in rows)
                message = f"{title} · {comparison}"
            else:
                message = f"{len(rows)} grupos · {title}"
            if operation == "maximo" and not group:
                tied = [r for r in filtered if r[metric] == value]
                if len(tied) == 1:
                    row = tied[0]
                    message += f" · {row['fecha']} vs. {row['rival']}"
                else:
                    message += f" · {len(tied)} partidos empatados"
        return dict(plan=plan, modo=mode, titulo=title, alcance=scope, base=len(filtered),
                    mensaje=message, columnas=columns, filas=rows, grafica=chart)
