"""M&M Reality: seznam nabídek z ld+json (ItemList), cena z textu odkazu.

Lokalita = část adresy, např. "ostrava": https://www.mmreality.cz/nemovitosti/pronajem/byty/<lokalita>/
"""
import json
import re

from bs4 import BeautifulSoup

from ..model import Offer, parse_price
from .base import ScraperBase

_KIND_URL = {"byt": "byty", "dum": "domy"}
_PRICE_RE = re.compile(r"(\d[\d\s]*)\s*Kč")


class MMReality(ScraperBase):
    name = "M&M Reality"
    key = "mmreality"
    color = "#d2232a"
    coarse_location = True

    def fetch_page(self, kind, area, page):
        url = f"https://www.mmreality.cz/nemovitosti/pronajem/{_KIND_URL[kind]}/{self.location_id(area)}/"
        if page > 1:
            url += f"?page={page}"
        soup = BeautifulSoup(self.get(url).text, "html.parser")
        items = []
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                graph = json.loads(script.string or "").get("@graph", [])
            except ValueError:
                continue
            for node in graph:
                main = node.get("mainEntity") or {}
                if main.get("@type") == "ItemList":
                    items = main.get("itemListElement", [])
        prices = {}
        for a in soup.find_all("a", href=re.compile(r"/nemovitosti/\d+/")):
            m = _PRICE_RE.search(a.get_text(" "))
            if m:
                prices.setdefault(a["href"].split("?")[0], " ".join(m.group(0).split()))
        offers = []
        for it in items:
            name = it.get("name", "")
            # "Pronájem, Byt 2+1, 55 m², Ostrava, Plzeňská" -> název a adresa
            parts = [p.strip() for p in name.split(",")]
            title = ", ".join(parts[:3]).replace("Pronájem, ", "Pronájem ") if len(parts) >= 3 else name
            price_text = prices.get(it["url"], "")
            offers.append(Offer(
                portal=self.name, link=it["url"], kind=kind, area_name=area.name, title=title,
                location=", ".join(parts[3:]), price=parse_price(price_text), price_text=price_text,
                image_url=it.get("image", "")))
        more = bool(soup.select_one(f'a[href*="page={page + 1}"]'))
        return offers, more
