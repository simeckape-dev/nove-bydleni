"""RE/MAX: HTML výpis. Lokalita = "kraj/okres" z formuláře hledání, např. "132/3807" (Ostrava-město)."""
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..model import Offer, parse_price
from .base import ScraperBase

# types[4][x] = dispozice bytu, types[6] = domy a vily
_DISP = {"1+kk": 2, "2+kk": 3, "3+kk": 4, "4+kk": 5, "1+1": 9, "2+1": 10, "3+1": 11, "4+1": 12,
         "5+": (6, 7, 8, 13, 14, 15), "atyp": (16, 17)}


class Remax(ScraperBase):
    name = "RE/MAX"
    key = "remax"
    color = "#003da5"
    coarse_location = True
    base_url = "https://www.remax-czech.cz/reality/vyhledavani/"

    def fetch_page(self, kind, area, page):
        kraj, okres = str(self.location_id(area)).split("/")
        params = [f"regions%5B{kraj}%5D%5B{okres}%5D=on", "sale=2", "order_by_published_date=0"]
        if kind == "byt":
            for d in self.search.dispositions:
                v = _DISP[d]
                params += [f"types%5B4%5D%5B{x}%5D=on" for x in (v if isinstance(v, tuple) else (v,))]
        else:
            params.append("types%5B6%5D=on")
        if page > 1:
            params.append(f"stranka={page}")
        soup = BeautifulSoup(self.get(self.base_url + "?" + "&".join(params)).text, "html.parser")
        offers = []
        for it in soup.select(".pl-items .pl-items__item"):
            price_text = " ".join((it.get("data-price") or "").split())
            offers.append(Offer(
                portal=self.name, link=urljoin(self.base_url, it.get("data-url")), kind=kind, area_name=area.name,
                title=it.get("data-title") or "", location=re.sub(r"\s+", " ", it.get("data-display-address") or "").strip(" ,"),
                price=parse_price(price_text), price_text=price_text, image_url=it.get("data-img") or ""))
        more = bool(soup.select_one(f'a[href*="stranka={page + 1}"]'))
        return offers, more
