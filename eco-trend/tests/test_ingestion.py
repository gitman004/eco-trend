"""Tests de la collecte et du contrôle qualité, sans appel réseau (API simulée)."""

import csv
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd
import pytest
import requests

from ingestion.client import ApiError, OpenMeteoClient
from ingestion.collect import collect, merge_parts, part_path, rows_from_response, year_chunks
from ingestion.config import CITIES, COLUMNS, VARIABLES
from ingestion.quality import check

ROOT = Path(__file__).resolve().parents[1]


# --- API simulée -----------------------------------------------------------------

def fake_payload(start: str, end: str) -> dict:
    """Réponse au format Open-Meteo : une valeur par heure pour chaque variable."""
    t0 = datetime.fromisoformat(start)
    hours = int((datetime.fromisoformat(end) - t0).total_seconds() // 3600) + 24
    times = [(t0 + timedelta(hours=h)).strftime("%Y-%m-%dT%H:%M") for h in range(hours)]
    hourly = {"time": times}
    for i, var in enumerate(VARIABLES):
        hourly[var] = [10.0 + i] * hours
    return {"hourly": hourly}


class FakeResponse:
    def __init__(self, status=200, payload=None, headers=None):
        self.status_code = status
        self._payload = payload
        self.headers = headers or {}
        self.text = ""

    def json(self):
        return self._payload


class FakeSession:
    """Renvoie les réponses programmées puis, par défaut, des données valides."""

    def __init__(self, scripted=None):
        self.scripted = list(scripted or [])
        self.calls = []

    def get(self, url, params, timeout):
        self.calls.append(params)
        if self.scripted:
            item = self.scripted.pop(0)
            if isinstance(item, Exception):
                raise item
            return item
        return FakeResponse(200, fake_payload(params["start_date"], params["end_date"]))


def make_client(session, **kw):
    waits = []
    client = OpenMeteoClient(session=session, sleep=waits.append, **kw)
    return client, waits


# --- Découpage -------------------------------------------------------------------

def test_year_chunks_cover_period_without_gap_or_overlap():
    chunks = year_chunks(date(2023, 6, 15), date(2025, 2, 10))
    assert chunks == [
        (date(2023, 6, 15), date(2023, 12, 31)),
        (date(2024, 1, 1), date(2024, 12, 31)),
        (date(2025, 1, 1), date(2025, 2, 10)),
    ]


# --- Client ----------------------------------------------------------------------

def test_client_retries_on_rate_limit_and_respects_retry_after():
    session = FakeSession([FakeResponse(429, headers={"Retry-After": "42"}), FakeResponse(503)])
    client, waits = make_client(session, base_wait=10)
    data = client.fetch_hourly(48.8, 2.3, "2024-01-01", "2024-01-01")
    assert len(data["hourly"]["time"]) == 24
    assert waits == [42.0, 20.0]  # Retry-After, puis attente exponentielle (10 x 2)
    assert session.calls[0]["timezone"] == "GMT"


def test_client_retries_network_errors():
    session = FakeSession([requests.ConnectionError(), requests.Timeout()])
    client, waits = make_client(session)
    client.fetch_hourly(48.8, 2.3, "2024-01-01", "2024-01-01")
    assert len(waits) == 2


def test_client_gives_up_after_max_attempts():
    session = FakeSession([FakeResponse(429)] * 3)
    client, waits = make_client(session, max_attempts=3, base_wait=1)
    with pytest.raises(ApiError, match="3 tentatives"):
        client.fetch_hourly(48.8, 2.3, "2024-01-01", "2024-01-01")
    assert waits == [1, 2]


def test_client_fails_fast_on_bad_request():
    client, waits = make_client(FakeSession([FakeResponse(400)]))
    with pytest.raises(ApiError, match="HTTP 400"):
        client.fetch_hourly(48.8, 2.3, "2024-01-01", "2024-01-01")
    assert waits == []


# --- Conversion ------------------------------------------------------------------

def test_rows_follow_csv_column_order():
    rows = rows_from_response("Paris", fake_payload("2024-01-01", "2024-01-01"))
    assert len(rows) == 24
    assert len(rows[0]) == len(COLUMNS)
    assert rows[0][0] == "Paris" and rows[0][-1] == "2024-01-01T00:00"


def test_rows_reject_inconsistent_series():
    data = fake_payload("2024-01-01", "2024-01-01")
    data["hourly"]["rain"] = data["hourly"]["rain"][:-1]
    with pytest.raises(ValueError, match="rain"):
        rows_from_response("Paris", data)


# --- Collecte, reprise et fusion -------------------------------------------------

CITIES_2 = {"Paris": CITIES["Paris"], "Saint-Étienne": CITIES["Saint-Étienne"]}


def test_collect_resumes_without_refetching_or_duplicating(tmp_path):
    parts = tmp_path / "parts"
    start, end = date(2023, 12, 30), date(2024, 1, 2)

    # Premier passage interrompu au 3e appel (API indisponible)
    failing = FakeSession([FakeResponse(200, fake_payload("2023-12-30", "2023-12-31")),
                           FakeResponse(200, fake_payload("2024-01-01", "2024-01-02")),
                           FakeResponse(400)])
    client, _ = make_client(failing)
    with pytest.raises(ApiError):
        collect(client, CITIES_2, start, end, parts, delay=0)
    assert len(list(parts.glob("*.csv"))) == 2
    assert not list(parts.glob("*.tmp"))

    # Reprise : seuls les 2 appels manquants sont faits
    session = FakeSession()
    client, _ = make_client(session)
    paths = collect(client, CITIES_2, start, end, parts, delay=0)
    assert len(session.calls) == 2
    assert part_path(parts, "Saint-Étienne", date(2024, 1, 1), date(2024, 1, 2)).name == \
        "saint-etienne_2024-01-01_2024-01-02.csv"

    out = tmp_path / "meteo_data.csv"
    count = merge_parts(paths, out)
    assert count == 2 * 4 * 24  # 2 villes x 4 jours x 24 h
    df = pd.read_csv(out)
    assert list(df.columns) == COLUMNS
    assert check(df).ok


# --- Contrôle qualité ------------------------------------------------------------

def sample_df(hours=48, city="Paris"):
    rows = rows_from_response(city, fake_payload("2024-01-01", "2024-01-01"))[:0]
    t0 = datetime(2024, 1, 1)
    for h in range(hours):
        row = [city, *([5.0] * len(VARIABLES)), (t0 + timedelta(hours=h)).strftime("%Y-%m-%dT%H:%M")]
        rows.append(row)
    df = pd.DataFrame(rows, columns=COLUMNS)
    df["humidity_percent"] = 80.0
    df["pressure_msl_hpa"] = 1013.0
    return df


def test_quality_accepts_clean_data():
    r = check(sample_df())
    assert r.ok and r.duplicates == 0 and not r.missing_hours and not r.out_of_range


def test_quality_blocks_duplicates():
    df = sample_df()
    r = check(pd.concat([df, df.iloc[:5]]))
    assert not r.ok and r.duplicates == 5


def test_quality_reports_missing_hours_and_outliers_without_blocking():
    df = sample_df().drop(index=[10, 11, 12]).reset_index(drop=True)
    df.loc[0, "temperature_c"] = 75.0
    df.loc[1, "humidity_percent"] = None
    r = check(df)
    assert r.ok
    assert r.missing_hours == {"Paris": 3}
    assert r.out_of_range == {"temperature_c": 1}
    assert r.empty_values == {"humidity_percent": 1}


def test_quality_blocks_missing_columns():
    r = check(sample_df().drop(columns=["pressure_msl_hpa"]))
    assert not r.ok and "pressure_msl_hpa" in r.blocking[0]


# --- Cohérence entre fichiers ----------------------------------------------------

def test_hive_staging_schema_matches_csv_columns():
    sql = (ROOT / "hive" / "01_staging.sql").read_text(encoding="utf-8")
    create = sql.index("CREATE EXTERNAL TABLE")
    body = sql[sql.index("(", create) + 1: sql.index(")\nROW FORMAT")]
    names = [line.split()[0] for line in body.strip().splitlines() if line.strip()]
    assert names == COLUMNS


def test_cities_reference_file_matches_config():
    with (ROOT / "data" / "villes.csv").open(encoding="utf-8") as f:
        rows = list(csv.reader(f))
    assert [r[0] for r in rows] == list(CITIES)
    assert [(float(r[1]), float(r[2])) for r in rows] == list(CITIES.values())
