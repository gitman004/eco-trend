"""Contrôle qualité du CSV collecté, avant chargement dans HDFS.

    python -m ingestion.quality data/meteo_data.csv

Bloquant (code de sortie 1) : colonnes manquantes, doublons ville/heure,
fichier vide. Signalé sans bloquer : heures manquantes, valeurs vides,
valeurs physiquement aberrantes.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from .config import COLUMNS

# Bornes physiquement plausibles pour la France métropolitaine
RANGES = {
    "temperature_c": (-30, 48),
    "humidity_percent": (0, 100),
    "pressure_msl_hpa": (940, 1060),
    "precipitation_mm": (0, 200),
    "wind_speed_10m_kmh": (0, 250),
}


@dataclass
class Report:
    rows: int = 0
    rows_per_city: dict[str, int] = field(default_factory=dict)
    period: tuple[str, str] | None = None
    duplicates: int = 0
    missing_hours: dict[str, int] = field(default_factory=dict)
    empty_values: dict[str, int] = field(default_factory=dict)
    out_of_range: dict[str, int] = field(default_factory=dict)
    blocking: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.blocking


def check(df: pd.DataFrame) -> Report:
    r = Report(rows=len(df))
    missing_cols = [c for c in COLUMNS if c not in df.columns]
    if missing_cols:
        r.blocking.append(f"colonnes absentes : {', '.join(missing_cols)}")
        return r
    if df.empty:
        r.blocking.append("fichier vide")
        return r

    ts = pd.to_datetime(df["timestamp_utc"])
    r.period = (str(ts.min()), str(ts.max()))
    r.rows_per_city = df.groupby("city").size().to_dict()

    r.duplicates = int(df.duplicated(subset=["city", "timestamp_utc"]).sum())
    if r.duplicates:
        r.blocking.append(f"{r.duplicates} lignes en double (même ville et même heure)")

    # Complétude : chaque ville doit avoir une ligne par heure entre son début et sa fin
    for city, times in ts.groupby(df["city"]):
        expected = int((times.max() - times.min()) / pd.Timedelta(hours=1)) + 1
        gap = expected - times.nunique()
        if gap > 0:
            r.missing_hours[city] = gap

    empties = df[COLUMNS].isna().sum()
    r.empty_values = {c: int(n) for c, n in empties.items() if n}

    for col, (low, high) in RANGES.items():
        values = pd.to_numeric(df[col], errors="coerce")
        n = int(((values < low) | (values > high)).sum())
        if n:
            r.out_of_range[col] = n
    return r


def print_report(r: Report, path: Path) -> None:
    print(f"Contrôle qualité : {path}")
    print(f"  Lignes            : {r.rows:,}".replace(",", " "))
    if r.period:
        print(f"  Période (UTC)     : {r.period[0]} -> {r.period[1]}")
    if r.rows_per_city:
        print(f"  Villes            : {len(r.rows_per_city)}")
    print(f"  Doublons          : {r.duplicates}")
    print(f"  Heures manquantes : {sum(r.missing_hours.values())}"
          + (f" ({', '.join(f'{c} {n}' for c, n in r.missing_hours.items())})" if r.missing_hours else ""))
    if r.empty_values:
        print("  Valeurs vides     : " + ", ".join(f"{c} {n}" for c, n in r.empty_values.items()))
    if r.out_of_range:
        print("  Hors bornes       : " + ", ".join(f"{c} {n}" for c, n in r.out_of_range.items()))
    print("  Résultat          : " + ("OK" if r.ok else "BLOQUANT — " + " ; ".join(r.blocking)))


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Contrôle qualité du CSV météo")
    p.add_argument("csv", type=Path, nargs="?", default=Path("data/meteo_data.csv"))
    args = p.parse_args(argv)
    if not args.csv.exists():
        print(f"Fichier introuvable : {args.csv} (lancer d'abord python -m ingestion.collect)", file=sys.stderr)
        return 1
    report = check(pd.read_csv(args.csv))
    print_report(report, args.csv)
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
