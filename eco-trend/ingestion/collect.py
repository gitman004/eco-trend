"""Collecte de l'historique météo horaire des villes françaises.

    python -m ingestion.collect                       # 20 ans, 20 villes
    python -m ingestion.collect --cities Paris,Lyon --start 2024-01-01 --end 2024-12-31

Chaque appel à l'API (une ville, une année) est écrit dans son propre fichier
« part » de façon atomique (fichier temporaire puis renommage). Conséquences :
- une interruption ne laisse jamais de fichier à moitié écrit ;
- relancer la commande reprend là où elle s'était arrêtée, sans re-télécharger
  ni dupliquer de lignes ;
- le CSV final est reconstruit à partir des parts, donc toujours cohérent.
"""

from __future__ import annotations

import argparse
import csv
import logging
import os
import re
import time
import unicodedata
from datetime import date, timedelta
from pathlib import Path

from .client import OpenMeteoClient
from .config import CITIES, COLUMNS, VARIABLES

log = logging.getLogger("collect")


def year_chunks(start: date, end: date) -> list[tuple[date, date]]:
    """Découpe [start, end] en intervalles d'une année civile au plus, sans trou ni chevauchement."""
    chunks = []
    current = start
    while current <= end:
        chunk_end = min(date(current.year, 12, 31), end)
        chunks.append((current, chunk_end))
        current = chunk_end + timedelta(days=1)
    return chunks


def slug(name: str) -> str:
    ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", ascii_name.lower()).strip("-")


def part_path(parts_dir: Path, city: str, start: date, end: date) -> Path:
    return parts_dir / f"{slug(city)}_{start.isoformat()}_{end.isoformat()}.csv"


def rows_from_response(city: str, data: dict) -> list[list]:
    """Convertit la réponse de l'API en lignes CSV (ordre de config.COLUMNS)."""
    hourly = data["hourly"]
    times = hourly["time"]
    series = []
    for var in VARIABLES:
        values = hourly.get(var)
        if values is None:
            values = [None] * len(times)
        elif len(values) != len(times):
            raise ValueError(f"{city} : la variable {var} a {len(values)} valeurs pour {len(times)} heures")
        series.append(values)
    return [[city, *(s[i] for s in series), times[i]] for i in range(len(times))]


def write_part(path: Path, rows: list[list]) -> None:
    """Écriture atomique : le fichier final n'existe que s'il est complet."""
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(rows)
    os.replace(tmp, path)


def collect(
    client: OpenMeteoClient,
    cities: dict[str, tuple[float, float]],
    start: date,
    end: date,
    parts_dir: Path,
    delay: float = 5.0,
    sleep=time.sleep,
) -> list[Path]:
    """Télécharge les parts manquantes et renvoie la liste ordonnée de toutes les parts du plan."""
    parts_dir.mkdir(parents=True, exist_ok=True)
    chunks = year_chunks(start, end)
    plan = [(city, coords, a, b) for city, coords in cities.items() for a, b in chunks]
    done = sum(part_path(parts_dir, c, a, b).exists() for c, _, a, b in plan)
    log.info("%d villes x %d périodes = %d appels, %d déjà faits", len(cities), len(chunks), len(plan), done)

    paths = []
    first_call = True
    for i, (city, (lat, lon), a, b) in enumerate(plan, 1):
        path = part_path(parts_dir, city, a, b)
        paths.append(path)
        if path.exists():
            continue
        if not first_call and delay:
            sleep(delay)  # appels espacés pour rester sous les limites de l'API
        first_call = False
        data = client.fetch_hourly(lat, lon, a.isoformat(), b.isoformat())
        rows = rows_from_response(city, data)
        write_part(path, rows)
        log.info("[%d/%d] %s %s -> %s : %d lignes", i, len(plan), city, a, b, len(rows))
    return paths


def merge_parts(paths: list[Path], output: Path) -> int:
    """Assemble les parts en un seul CSV avec en-tête. Renvoie le nombre de lignes de données."""
    output.parent.mkdir(parents=True, exist_ok=True)
    tmp = output.with_suffix(".tmp")
    count = 0
    with tmp.open("w", newline="", encoding="utf-8") as out:
        writer = csv.writer(out)
        writer.writerow(COLUMNS)
        for path in paths:
            with path.open(newline="", encoding="utf-8") as f:
                for row in csv.reader(f):
                    writer.writerow(row)
                    count += 1
    os.replace(tmp, output)
    return count


def parse_args(argv=None):
    yesterday = date.today() - timedelta(days=1)
    p = argparse.ArgumentParser(description="Collecte de l'historique météo horaire (Open-Meteo)")
    twenty_years_ago = date(yesterday.year - 20, yesterday.month, min(yesterday.day, 28))
    p.add_argument("--start", type=date.fromisoformat, default=twenty_years_ago)
    p.add_argument("--end", type=date.fromisoformat, default=yesterday)
    p.add_argument("--cities", help="Liste séparée par des virgules (par défaut : les 20 villes)")
    p.add_argument("--data-dir", type=Path, default=Path("data"))
    p.add_argument("--delay", type=float, default=5.0, help="Secondes entre deux appels à l'API")
    return p.parse_args(argv)


def main(argv=None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")
    args = parse_args(argv)
    if args.cities:
        names = [c.strip() for c in args.cities.split(",")]
        unknown = [n for n in names if n not in CITIES]
        if unknown:
            raise SystemExit(f"Villes inconnues : {', '.join(unknown)}")
        cities = {n: CITIES[n] for n in names}
    else:
        cities = CITIES
    if args.start > args.end:
        raise SystemExit("--start doit précéder --end")

    paths = collect(OpenMeteoClient(), cities, args.start, args.end, args.data_dir / "parts", args.delay)
    output = args.data_dir / "meteo_data.csv"
    count = merge_parts(paths, output)
    log.info("Terminé : %d lignes dans %s", count, output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
