"""Client de l'API d'archives Open-Meteo, avec réessais bornés.

L'API est gratuite et sans clé, mais limite le nombre d'appels. Le client :
- réessaie les erreurs temporaires (429, 5xx, coupure réseau, timeout) avec une
  attente exponentielle, en respectant l'en-tête Retry-After quand il est fourni ;
- abandonne après un nombre maximal de tentatives, au lieu de boucler indéfiniment ;
- échoue tout de suite sur une erreur définitive (400 : paramètre invalide).
"""

from __future__ import annotations

import logging
import time
from typing import Any, Callable

import requests

from .config import VARIABLES

log = logging.getLogger(__name__)

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"


class ApiError(RuntimeError):
    pass


class OpenMeteoClient:
    def __init__(
        self,
        session: Any | None = None,
        max_attempts: int = 6,
        base_wait: float = 15.0,
        max_wait: float = 900.0,
        timeout: float = 120.0,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self.session = session or requests.Session()
        self.max_attempts = max_attempts
        self.base_wait = base_wait
        self.max_wait = max_wait
        self.timeout = timeout
        self.sleep = sleep

    def _backoff(self, attempt: int, retry_after: str | None = None) -> float:
        if retry_after and retry_after.isdigit():
            return min(float(retry_after), self.max_wait)
        return min(self.base_wait * 2 ** (attempt - 1), self.max_wait)

    def fetch_hourly(self, lat: float, lon: float, start: str, end: str) -> dict:
        """Données horaires (heures UTC) entre deux dates incluses, au format brut de l'API."""
        params = {
            "latitude": lat,
            "longitude": lon,
            "start_date": start,
            "end_date": end,
            "hourly": ",".join(VARIABLES),
            "timezone": "GMT",  # UTC : pas d'heure en double ni manquante aux changements d'heure
        }
        last_error = ""
        for attempt in range(1, self.max_attempts + 1):
            retry_after = None
            try:
                resp = self.session.get(ARCHIVE_URL, params=params, timeout=self.timeout)
            except (requests.Timeout, requests.ConnectionError) as exc:
                last_error = f"{type(exc).__name__}"
            else:
                if resp.status_code == 200:
                    data = resp.json()
                    if "hourly" in data and "time" in data["hourly"]:
                        return data
                    last_error = "réponse sans données horaires"
                elif resp.status_code == 429 or resp.status_code >= 500:
                    last_error = f"HTTP {resp.status_code}"
                    retry_after = resp.headers.get("Retry-After")
                else:
                    raise ApiError(f"HTTP {resp.status_code} : {resp.text[:200]}")

            if attempt < self.max_attempts:
                wait = self._backoff(attempt, retry_after)
                log.warning("%s (tentative %d/%d), nouvel essai dans %.0f s",
                            last_error, attempt, self.max_attempts, wait)
                self.sleep(wait)

        raise ApiError(f"Échec après {self.max_attempts} tentatives : {last_error}")
