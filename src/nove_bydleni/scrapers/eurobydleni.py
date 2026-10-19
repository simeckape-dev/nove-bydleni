"""EuroBydlení.cz: formulář hledání (POST), výsledky jako HTML.

Lokalita = {nazev: "Ostrava, Česko", stred: [lat, lng], hranice: [sever, východ, jih, západ]}.
"""
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..model import Offer, parse_price
from .base import ScraperBase

_TYPE = {"byt": 7, "dum": 8}
_DISP = {"1+1": 15, "1+kk": 16, "2+1": 17, "2+kk": 18, "3+1": 19, "3+kk": 20, "4+1": 21, "4+kk": 22,
         "5+": (202, 256), "atyp": (14, 857)}
_RENT = 3


class EuroBydleni(ScraperBase):
    name = "EuroBydlení"
    key = "eurobydleni"
    color = "#0d47a1"
    coarse_location = True
    base_url = "https://www.eurobydleni.cz/search-form"

    def fetch_page(self, kind, area, page):
        loc = self.location_id(area)
        north, east, south, west = loc["hranice"]
        lat, lng = loc["stred"]
        data = {
            "sql[advert_type_eu][]": _TYPE[kind], "sql[advert_function_eu][]": _RENT,
            "sql[locality][locality][input]": loc["nazev"], "sql[locality][locality][city]": loc["nazev"],
            "sql[locality][locality][zip_code]": "", "sql[locality][locality][types]": "locality",
            "sql[locality][location][lat]": lat, "sql[locality][location][lng]": lng,
            "sql[locality][viewport][south]": south, "sql[locality][viewport][west]": west,
            "sql[locality][viewport][north]": north, "sql[locality][viewport][east]": east,
        }
        if kind == "byt":
            disp = []
            for d in self.search.dispositions:
                v = _DISP[d]
                disp += list(v) if isinstance(v, tuple) else [v]
            data["sql[advert_subtype_eu][]"] = disp
        if page > 1:
            data["page"] = page
        r = self.post(self.base_url, data=data, cookies={"listing-sort": "sort-added"})
        r.encoding = "utf-8"
        soup = BeautifulSoup(r.text, "html.parser")
        box = soup.find(id="properties-box")
        if box is None:
            return [], False
        offers = []
        for it in box.find_all("li", class_="list-items__item"):
            content = it.find("div", class_="list-items__content__1")
            title = content.find("h2", class_="list-items__item__title")
            details = content.find_all("li")
            img = it.select_one("ul.list-items__item__image__wrap img")
            price_text = " ".join(details[0].get_text().split()) if details else ""
            src = img.get("src", "") if img else ""
            offers.append(Offer(
                portal=self.name, link=urljoin(self.base_url, title.find("a")["href"]), kind=kind, area_name=area.name,
                title=" ".join(title.get_text().split()),
                location=" ".join(details[1].get_text().split()) if len(details) > 1 else "",
                price=parse_price(price_text), price_text=price_text,
                image_url=("https:" + src) if src.startswith("//") else src))
        more = bool(soup.select_one('a[rel="next"], .pagination a.next, a.paging__next'))
        return offers, more
