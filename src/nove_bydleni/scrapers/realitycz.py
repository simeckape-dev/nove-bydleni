"""Reality.cz: HTML výpis. Lokalita = část adresy, např. "okres-Ostrava-mesto" nebo "Frydek-Mistek":
https://www.reality.cz/pronajem/byty/<lokalita>/
"""
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..model import Offer, parse_price
from .base import ScraperBase

_KIND_URL = {"byt": "byty", "dum": "domy"}


class RealityCz(ScraperBase):
    name = "Reality.cz"
    key = "realitycz"
    color = "#e30613"

    def fetch_page(self, kind, area, page):
        base = f"https://www.reality.cz/pronajem/{_KIND_URL[kind]}/{self.location_id(area)}/"
        url = base + (f"?strana={page}" if page > 1 else "")
        soup = BeautifulSoup(self.get(url).text, "html.parser")
        offers = []
        for it in soup.select("div.xvypis"):
            a = it.select_one("p.vypisnaz a")
            if not a:
                continue
            code = a["href"].split("/")[0]
            info = " ".join(it.select_one("p.lokalita").get_text().split()) if it.select_one("p.lokalita") else ""
            price_el = it.select_one("p.vypiscena")
            price_text = " ".join(price_el.get_text().split()) if price_el else ""
            img = it.select_one(".thumbnail img")
            offers.append(Offer(
                portal=self.name, link=f"https://www.reality.cz/{code}/", kind=kind, area_name=area.name,
                title=f"Pronájem {info}".strip(), location=" ".join(a.get_text().split()),
                price=parse_price(price_text.replace(".", "")), price_text=price_text,
                image_url=urljoin("https://www.reality.cz/", img["src"]) if img else ""))
        more = bool(soup.select_one(f'a[href*="strana={page + 1}"]'))
        return offers, more
