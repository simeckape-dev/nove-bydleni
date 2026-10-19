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

    def cycle(self):
        self.running = True
        started = time.time()
        total_new = 0
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
        log.info("Kolo hotovo za %.0f s, nových nabídek %d", time.time() - started, total_new)

    def run_now(self):
        """Spustí kolo co nejdřív (tlačítko na stavové stránce)."""
        self._wake.set()

    def loop(self):
        while True:
            self.cycle()
            wait = self.interval_minutes() * 60
            self.next_cycle = time.time() + wait
            self._wake.wait(wait)
            self._wake.clear()

    def start(self):
        threading.Thread(target=self.loop, name="runner", daemon=True).start()
