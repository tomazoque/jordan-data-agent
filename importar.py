"""Extrae y valida la carrera NBA de Michael Jordan desde PlayerStatistics.csv."""

import argparse
import csv
from collections import Counter
from datetime import date
from decimal import Decimal
from pathlib import Path


FIELDS = {
    "pts": "points", "fgm": "fieldGoalsMade", "fga": "fieldGoalsAttempted",
    "3pm": "threePointersMade", "3pa": "threePointersAttempted",
    "ftm": "freeThrowsMade", "fta": "freeThrowsAttempted",
    "reb": "reboundsTotal", "ast": "assists", "stl": "steals", "blk": "blocks",
}
PHASES = {"Regular Season": "Regular", "Playoffs": "Playoffs"}
EXPECTED = {
    "Regular": (1072, 32292, 581, 69),
    "Playoffs": (179, 5987, 148, 63),
}


def import_games(path):
    games = []
    seen = set()
    skipped = Counter()
    with path.open(encoding="utf-8-sig", newline="") as source:
        for row in csv.DictReader(source):
            if row["personId"] != "893":
                continue
            phase = PHASES.get(row["gameType"])
            if phase is None or float(row["numMinutes"] or 0) <= 0:
                skipped[(row["gameType"], row["comment"])] += 1
                continue
            game_id = str(int(row["gameId"])).zfill(10)
            if game_id in seen:
                raise ValueError(f"Partido duplicado: {game_id}")
            seen.add(game_id)
            played = date.fromisoformat(row["gameDateTimeEst"][:10])
            start = played.year - (played.month < 9)
            expected_prefix = f"00{2 if phase == 'Regular' else 4}{start % 100:02}"
            if not game_id.startswith(expected_prefix):
                raise ValueError(f"Fecha y código de temporada no coinciden: {game_id}")
            numbers = {field: Decimal(row[source]) for field, source in FIELDS.items()}
            if any(number != int(number) for number in numbers.values()):
                raise ValueError(f"Estadística no entera: {game_id}")
            stats = {field: int(number) for field, number in numbers.items()}
            if not (0 <= stats["3pm"] <= stats["fgm"] <= stats["fga"]
                    and 0 <= stats["3pm"] <= stats["3pa"] <= stats["fga"]
                    and 0 <= stats["ftm"] <= stats["fta"]):
                raise ValueError(f"Tiros incoherentes: {game_id}")
            if stats["pts"] != 2 * stats["fgm"] + stats["3pm"] + stats["ftm"]:
                raise ValueError(f"Puntos incoherentes: {game_id}")
            if any(n < 0 for n in stats.values()):
                raise ValueError(f"Estadística negativa: {game_id}")
            games.append({
                "id": game_id, "fecha": played.isoformat(),
                "temporada": f"{start}-{(start + 1) % 100:02}",
                "fase": phase, "equipo": row["playerteamName"],
                "rival": f'{row["opponentteamCity"]} {row["opponentteamName"]}',
                "local": int(row["home"]), "victoria": int(row["win"]),
                "min": round(float(row["numMinutes"]), 4), **stats,
            })
    for phase, expected in EXPECTED.items():
        rows = [row for row in games if row["fase"] == phase]
        actual = (len(rows), sum(r["pts"] for r in rows), sum(r["3pm"] for r in rows),
                  max((r["pts"] for r in rows), default=0))
        if actual != expected:
            raise ValueError(f"{phase}: {actual} frente a {expected} (PJ, PTS, 3PM, máximo)")
        print(f"{phase}: {actual} (PJ, PTS, 3PM, máximo)")
    print(f"Excluidos por fase o minutos: {dict(skipped)}")
    return sorted(games, key=lambda row: row["fecha"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archivo", type=Path)
    parser.add_argument("--salida", type=Path, default=Path("data/jordan.csv"))
    args = parser.parse_args()
    games = import_games(args.archivo)
    with args.salida.open("w", encoding="utf-8", newline="") as target:
        writer = csv.DictWriter(target, games[0].keys(), lineterminator="\n")
        writer.writeheader()
        writer.writerows(games)


if __name__ == "__main__":
    main()
