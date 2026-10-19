"""Společný základ scraperů: HTTP relace, stránkování a filtr dispozic."""
import logging
import time
from abc import ABC, abstractmethod

import requests

from ..config import Area, Search
from ..model import Offer

log = logging.getLogger(__name__)


class NotSupported(Exception):
    """Portál pro daný typ nebo lokalitu nic nenabízí (např. chybí identifikátor lokality)."""


class ScraperBase(ABC):
    name: str = ""
    """Zobrazovaný název portálu"""
    key: str = ""
    """Klíč portálu v konfiguraci lokalit (např. "sreality")"""
    color: str = "#888888"
    coarse_location = False
    """Portál hledá jen v okrese nebo obdélníku na mapě: nabídky se navíc filtrují podle obcí lokality"""
    page_delay = 1.0
    """Pauza mezi stránkami, ať portály nezatěžujeme"""
    user_agent = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/141.0.0.0 Safari/537.36")

    def __init__(self, search: Search):
        self.search = search
        self.http = requests.Session()
        self.http.headers.update({"User-Agent": self.user_agent, "Accept-Language": "cs,en;q=0.8"})

    def get(self, url, **kw) -> requests.Response:
        r = self.http.get(url, timeout=kw.pop("timeout", 30), **kw)
        r.raise_for_status()
        return r

    def post(self, url, **kw) -> requests.Response:
        r = self.http.post(url, timeout=kw.pop("timeout", 30), **kw)
        r.raise_for_status()
        return r

    def location_id(self, area: Area):
        lid = area.get(self.key)
        if lid is None:
            raise NotSupported(f"lokalita {area.name!r} nemá identifikátor pro {self.key}")
        return lid

    @abstractmethod
    def fetch_page(self, kind: str, area: Area, page: int) -> tuple[list[Offer], bool]:
        """Stáhne jednu stránku výsledků (číslováno od 1). Vrací (nabídky, jsou_další_stránky)."""

    def fetch(self, kind: str, area: Area) -> tuple[list[Offer], bool]:
        """Stáhne až max_pages stránek. Vrací (nabídky po filtru dispozic, staženo_vše)."""
        offers: dict[str, Offer] = {}
        complete = False
        for page in range(1, self.search.max_pages + 1):
            items, more = self.fetch_page(kind, area, page)
            new_links = [o.link for o in items if o.link not in offers]
            for o in items:
                offers.setdefault(o.link, o)
            if not more or not items or not new_links:
                complete = True
                break
            time.sleep(self.page_delay)
        return [o for o in offers.values() if self.wanted(o) and self.in_area(o, area)], complete

    def in_area(self, offer: Offer, area: Area) -> bool:
        towns = area.towns
        if not self.coarse_location or not towns:
            return True
        loc = offer.location.lower()
        return any(t.lower() in loc for t in towns)

    def wanted(self, offer: Offer) -> bool:
        if offer.disposition is None:
            return self.search.keep_unknown_disposition
        return offer.disposition in self.search.dispositions
