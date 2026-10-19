"""Nastavení: hledání ze souboru YAML (CONFIG_FILE), provoz z proměnných prostředí."""
import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .model import DISPOSITIONS, KINDS


@dataclass
class Area:
    """Hledaná lokalita. Každý portál má vlastní identifikátor místa (klíč = jméno portálu)."""

    name: str
    portals: dict = field(default_factory=dict)
    towns: list[str] = field(default_factory=list)
    """Obce lokality; u portálů, které hledají jen v okrese, se nabídky mimo ně zahodí"""

    def get(self, portal: str):
        return self.portals.get(portal)


@dataclass
class Search:
    kinds: list[str]
    dispositions: list[str]
    keep_unknown_disposition: bool
    """Nechat nabídky, u kterých nejde dispozici zjistit (časté u domů)"""
    areas: list[Area]
    max_pages: int
    portals: list[str] | None
    """Povolené portály (None = všechny)"""


@dataclass
class Settings:
    config_file: Path
    data_dir: Path
    interval_day_min: int
    interval_night_min: int
    listen: str
    port: int
    debug: bool


def load_settings() -> Settings:
    env = os.environ.get
    return Settings(
        config_file=Path(env("CONFIG_FILE", "config/hledani.yaml")),
        data_dir=Path(env("DATA_DIR", "data")),
        interval_day_min=int(env("REFRESH_INTERVAL_DAYTIME_MINUTES", "30")),
        interval_night_min=int(env("REFRESH_INTERVAL_NIGHTTIME_MINUTES", "90")),
        listen=env("LISTEN", "0.0.0.0"),
        port=int(env("PORT", "8080")),
        debug=env("DEBUG", "0").lower() in ("1", "true", "yes"),
    )


def load_search(path: Path) -> Search:
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    kinds = raw.get("typy", list(KINDS))
    disps = [str(d) for d in raw.get("dispozice", DISPOSITIONS)]
    for k in kinds:
        if k not in KINDS:
            raise ValueError(f"neznámý typ {k!r}, povolené: {KINDS}")
    for d in disps:
        if d not in DISPOSITIONS:
            raise ValueError(f"neznámá dispozice {d!r}, povolené: {DISPOSITIONS}")
    areas = [Area(name=a["nazev"], towns=a.get("obce", []),
                  portals={k: v for k, v in a.items() if k not in ("nazev", "obce")}) for a in raw.get("lokality", [])]
    if not areas:
        raise ValueError("v konfiguraci chybí lokality")
    return Search(
        kinds=kinds,
        dispositions=disps,
        keep_unknown_disposition=bool(raw.get("nechat_neznamou_dispozici", True)),
        areas=areas,
        max_pages=int(raw.get("max_stranek", 5)),
        portals=raw.get("portaly"),
    )
