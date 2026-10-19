"""Úložiště nabídek a stavu portálů v SQLite."""
import json
import sqlite3
import threading
import time
from pathlib import Path

from .model import Offer

_SCHEMA = """
CREATE TABLE IF NOT EXISTS offers (
    link        TEXT PRIMARY KEY,
    portal      TEXT NOT NULL,
    kind        TEXT NOT NULL,
    area_name   TEXT NOT NULL,
    title       TEXT NOT NULL,
    location    TEXT NOT NULL,
    price       INTEGER,
    price_text  TEXT NOT NULL DEFAULT '',
    image_url   TEXT NOT NULL DEFAULT '',
    disposition TEXT,
    surface     INTEGER,
    first_seen  REAL NOT NULL,
    last_seen   REAL NOT NULL,
    gone_at     REAL,
    silent      INTEGER NOT NULL DEFAULT 0,
    price_history TEXT NOT NULL DEFAULT '[]'
);
CREATE INDEX IF NOT EXISTS offers_first_seen ON offers(first_seen);
CREATE TABLE IF NOT EXISTS portal_runs (
    portal      TEXT NOT NULL,
    kind        TEXT NOT NULL,
    area_name   TEXT NOT NULL,
    last_run    REAL NOT NULL,
    last_ok     REAL,
    found       INTEGER NOT NULL DEFAULT 0,
    error       TEXT,
    PRIMARY KEY (portal, kind, area_name)
);
"""


class Storage:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(path, check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        self._db.execute("PRAGMA journal_mode=WAL")
        self._db.executescript(_SCHEMA)
        self._lock = threading.Lock()

    def portal_seen_before(self, portal: str, kind: str, area_name: str) -> bool:
        """Proběhlo už pro tuhle kombinaci úspěšné stažení? Jinak jsou všechny nabídky "staré" (první běh)."""
        row = self._db.execute(
            "SELECT last_ok FROM portal_runs WHERE portal=? AND kind=? AND area_name=?", (portal, kind, area_name)).fetchone()
        return bool(row and row["last_ok"])

    def save_run(self, portal: str, kind: str, area_name: str, offers: list[Offer], error: str | None,
                 complete: bool = True) -> int:
        """Uloží výsledek jednoho stažení a vrátí počet nových nabídek."""
        now = time.time()
        new = 0
        with self._lock, self._db:
            silent = 0 if self.portal_seen_before(portal, kind, area_name) else 1
            for o in offers:
                row = self._db.execute("SELECT price, price_history FROM offers WHERE link=?", (o.link,)).fetchone()
                if row is None:
                    self._db.execute(
                        "INSERT INTO offers (link, portal, kind, area_name, title, location, price, price_text, image_url,"
                        " disposition, surface, first_seen, last_seen, silent) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        (o.link, o.portal, o.kind, o.area_name, o.title, o.location, o.price, o.price_text, o.image_url,
                         o.disposition, o.surface, now, now, silent))
                    new += 1 - silent
                else:
                    history = json.loads(row["price_history"])
                    if o.price and row["price"] and o.price != row["price"]:
                        history.append({"t": now, "old": row["price"], "new": o.price})
                    self._db.execute(
                        "UPDATE offers SET title=?, location=?, price=?, price_text=?, image_url=?, disposition=?, surface=?,"
                        " last_seen=?, gone_at=NULL, price_history=? WHERE link=?",
                        (o.title, o.location, o.price, o.price_text, o.image_url, o.disposition, o.surface, now,
                         json.dumps(history), o.link))
            if error is None:
                # Co při úplném stažení (všechny stránky) chybí, z portálu zmizelo
                if offers and complete:
                    links = [o.link for o in offers]
                    self._db.execute(
                        f"UPDATE offers SET gone_at=? WHERE portal=? AND kind=? AND area_name=? AND gone_at IS NULL"
                        f" AND link NOT IN ({','.join('?' * len(links))})", (now, portal, kind, area_name, *links))
                self._db.execute(
                    "INSERT INTO portal_runs (portal, kind, area_name, last_run, last_ok, found, error) VALUES (?,?,?,?,?,?,NULL)"
                    " ON CONFLICT(portal, kind, area_name) DO UPDATE SET last_run=excluded.last_run, last_ok=excluded.last_ok,"
                    " found=excluded.found, error=NULL", (portal, kind, area_name, now, now, len(offers)))
            else:
                self._db.execute(
                    "INSERT INTO portal_runs (portal, kind, area_name, last_run, found, error) VALUES (?,?,?,?,0,?)"
                    " ON CONFLICT(portal, kind, area_name) DO UPDATE SET last_run=excluded.last_run, error=excluded.error",
                    (portal, kind, area_name, now, error))
        return new

    def offers(self, include_gone: bool = False) -> list[sqlite3.Row]:
        q = "SELECT * FROM offers" + ("" if include_gone else " WHERE gone_at IS NULL") + " ORDER BY first_seen DESC, rowid DESC"
        return self._db.execute(q).fetchall()

    def runs(self) -> list[sqlite3.Row]:
        return self._db.execute("SELECT * FROM portal_runs ORDER BY portal, area_name, kind").fetchall()
