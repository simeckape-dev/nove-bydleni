"""Pravidelné stahování nabídek ze všech portálů."""
import logging
import threading
import time
import traceback
from datetime import datetime

from .config import Search, Settings
from .scrapers import ALL
from .scrapers.base import NotSupported
from .storage import Storage

log = logging.getLogger(__name__)

RETRY_SECONDS = 120
"""Když celé kolo selže (typicky hned po startu, než naběhne DNS clusteru), další pokus za 2 minuty"""


class Runner:
    def __init__(self, settings: Settings, search: Search, storage: Storage):
        self.settings = settings
        self.search = search
        self.storage = storage
        self.scrapers = [cls(search) for cls in ALL if not search.portals or cls.key in search.portals]
        self.running = False
        self.last_cycle: float | None = None
        self.next_cycle: float | None = None
        self._wake = threading.Event()

    def interval_minutes(self) -> int:
        return self.settings.interval_day_min if 6 <= datetime.now().hour < 22 else self.settings.interval_night_min

    def cycle(self) -> bool:
        """Jedno kolo stahování; vrací True, když aspoň jeden portál uspěl."""
        self.running = True
        started = time.time()
        total_new = 0
        ok = 0
        try:
            for sc in self.scrapers:
                for area in self.search.areas:
                    if area.get(sc.key) is None:
                        continue
                    for kind in self.search.kinds:
                        try:
                            offers, complete = sc.fetch(kind, area)
                            new = self.storage.save_run(sc.name, kind, area.name, offers, None, complete)
                            total_new += new
                            ok += 1
                            log.info("%s / %s / %s: %d nabídek, nových %d", sc.name, area.name, kind, len(offers), new)
                        except NotSupported:
                            continue
                        except Exception as e:
                            log.error("%s / %s / %s: %s", sc.name, area.name, kind, e)
                            log.debug(traceback.format_exc())
                            self.storage.save_run(sc.name, kind, area.name, [], f"{type(e).__name__}: {e}"[:500])
        finally:
            self.running = False
            self.last_cycle = time.time()
        log.info("Kolo hotovo za %.0f s, nových nabídek %d, úspěšných stažení %d", time.time() - started, total_new, ok)
        return ok > 0

    def run_now(self):
        """Spustí kolo co nejdřív (tlačítko na stavové stránce)."""
        self._wake.set()

    def loop(self):
        while True:
            wait = self.interval_minutes() * 60 if self.cycle() else RETRY_SECONDS
            self.next_cycle = time.time() + wait
            self._wake.wait(wait)
            self._wake.clear()

    def start(self):
        threading.Thread(target=self.loop, name="runner", daemon=True).start()
