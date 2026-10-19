"""iDNES Reality: HTML výpis.

Lokalita = část adresy, např. "ostrava": https://reality.idnes.cz/s/pronajem/byty/<lokalita>/
"""
import re

from bs4 import BeautifulSoup

from ..model import Offer, parse_price
from .base import ScraperBase

_KIND_URL = {"byt": "byty", "dum": "domy"}
_SUBTYPE = {"1+kk": "1k", "1+1": "11", "2+kk": "2k", "2+1": "21", "3+kk": "3k", "3+1": "31", "4+kk": "4k", "4+1": "41",
            "5+": ("5k", "51", "6k"), "atyp": "atypical"}


class Idnes(ScraperBase):
    name = "iDNES Reality"
    key = "idnes"
    color = "#1d80d7"

    def fetch_page(self, kind, area, page):
        url = f"https://reality.idnes.cz/s/pronajem/{_KIND_URL[kind]}/{self.location_id(area)}/"
        params = []
        if kind == "byt":
            for d in self.search.dispositions:
                v = _SUBTYPE[d]
                params += [f"s-qc%5BsubtypeFlat%5D%5B%5D={x}" for x in (v if isinstance(v, tuple) else (v,))]
        if page > 1:
            params.append(f"page={page - 1}")
        if params:
            url += "?" + "&".join(params)
        soup = BeautifulSoup(self.get(url).text, "html.parser")
        box = soup.find(id="snippet-s-result-articles")
        if box is None:
            raise RuntimeError("chybí výpis výsledků (změna webu?)")
        offers = []
        for it in box.find_all("div", class_="c-products__item"):
            if "c-products__item-advertisment" in it.get("class", []):
                continue
            a = it.find("a", class_="c-products__link")
            if not a:
                continue
            img = it.find("img")
            price_el = it.find("p", class_="c-products__price")
            price_text = " ".join(price_el.get_text().split()) if price_el else ""
            offers.append(Offer(
                portal=self.name, link=a["href"].split("?")[0], kind=kind, area_name=area.name,
                title=" ".join(it.find("h2", class_="c-products__title").get_text().split()),
                location=" ".join(it.find("p", class_="c-products__info").get_text().split()),
                price=parse_price(price_text), price_text=price_text,
                image_url=(img.get("data-src") or img.get("src") or "") if img else ""))
        more = bool(soup.select_one("a.paging__item.next, a.btn--paging-next, a[rel=next]"))
        return offers, more
