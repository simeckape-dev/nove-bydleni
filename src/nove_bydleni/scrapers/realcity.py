"""REALCITY.cz: HTML výpis s filtrem v parametru sp (JSON). Lokalita = číslo okresu, např. 87 (Ostrava-město)."""
import json
import re
from urllib.parse import quote

from bs4 import BeautifulSoup

from ..model import Offer, parse_price
from .base import ScraperBase

_DISP = {"1+kk": "1+kk", "1+1": "1+1", "2+kk": "2+kk", "2+1": "2+1", "3+kk": "3+kk", "3+1": "3+1", "4+kk": "4+kk",
         "4+1": ("4+1", "4+2"), "5+": ("5+kk", "5+1", "5+2", "6+kk", "6+1", "disp_more"), "atyp": ("atyp", "disp_nospec")}
_URL = {"byt": "pronajem-bytu", "dum": "pronajem-domu"}
_TYPE = {"byt": "flat", "dum": "house"}


class Realcity(ScraperBase):
    name = "REALCITY"
    key = "realcity"
    color = "#b60d1c"
    coarse_location = True

    def fetch_page(self, kind, area, page):
        ptype = {"propertyType": _TYPE[kind]}
        if kind == "byt":
            disp = []
            for d in self.search.dispositions:
                v = _DISP[d]
                disp += list(v) if isinstance(v, tuple) else [v]
            ptype["options"] = {"disposition": disp}
        sp = {"locality": [int(self.location_id(area))], "transactionTypes": ["rent"], "propertyTypes": [ptype]}
        url = f"https://www.realcity.cz/{_URL[kind]}/?sp={quote(json.dumps(sp, separators=(',', ':')))}"
        if page > 1:
            url += f"&list-page={page}"
        soup = BeautifulSoup(self.get(url).text, "html.parser")
        offers = []
        for it in soup.select("#rc-advertise-result .media.advertise.item"):
            body = it.find("div", class_="media-body")
            title = body.find("div", class_="title").a
            img = it.select_one("div.image img")
            price_text = " ".join(body.find("div", class_="price").get_text().split())
            src = img.get("src", "") if img else ""
            offers.append(Offer(
                portal=self.name, link="https://www.realcity.cz" + title.get("href"), kind=kind, area_name=area.name,
                title=title.get_text().strip(), location=" ".join(body.find("div", class_="address").get_text().split()),
                price=parse_price(price_text), price_text=price_text,
                image_url=("https:" + src) if src.startswith("//") else src))
        more = bool(soup.select_one(f'a[href*="list-page={page + 1}"]'))
        return offers, more
