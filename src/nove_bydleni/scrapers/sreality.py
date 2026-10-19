"""Sreality.cz: data z __NEXT_DATA__ stránky vyhledávání.

Lokalita = část adresy hledání, např. "ostrava" (město) nebo "frydek-mistek" (okres), případně s parametrem,
který okres zúží na město: "frydek-mistek?region=obec-frydek-mistek".
https://www.sreality.cz/hledani/pronajem/byty/<lokalita>
"""
import json
import re
from urllib.parse import quote

from ..model import Offer
from .base import ScraperBase

_KIND_URL = {"byt": "byty", "dum": "domy"}
_CAT_TYPE = {1: "prodej", 2: "pronajem", 3: "drazby"}
_CAT_MAIN = {1: "byt", 2: "dum"}
_CAT_SUB = {2: "1+kk", 3: "1+1", 4: "2+kk", 5: "2+1", 6: "3+kk", 7: "3+1", 8: "4+kk", 9: "4+1", 10: "5+kk", 11: "5+1",
            12: "6-a-vice", 16: "atypicky", 47: "pokoj", 37: "rodinny", 39: "vila", 43: "chalupa", 33: "chata",
            35: "pamatka", 40: "na-klic", 44: "zemedelska-usedlost", 53: "mobilni-domek", 36: "jine-nemovitosti"}
# Dispozice pro parametr velikost (jen byty)
_SIZE = {"1+kk": "1+kk", "1+1": "1+1", "2+kk": "2+kk", "2+1": "2+1", "3+kk": "3+kk", "3+1": "3+1",
         "4+kk": "4+kk", "4+1": "4+1", "5+": "5+kk,5+1,6-a-vice", "atyp": "atypicky"}


class Sreality(ScraperBase):
    name = "Sreality"
    key = "sreality"
    color = "#cc0000"
    base_url = "https://www.sreality.cz"

    def _link(self, item) -> str:
        loc = item["locality"]
        parts = [loc.get("citySeoName"), loc.get("cityPartSeoName"), loc.get("streetSeoName")]
        return (f"{self.base_url}/detail/{_CAT_TYPE.get(item['categoryTypeCb']['value'], 'pronajem')}/"
                f"{_CAT_MAIN.get(item['categoryMainCb']['value'], 'byt')}/"
                f"{_CAT_SUB.get(item['categorySubCb']['value'], 'ostatni')}/"
                f"{'-'.join(p for p in parts if p)}/{item['id']}")

    def fetch_page(self, kind, area, page):
        path, _, query = str(self.location_id(area)).partition("?")
        url = f"{self.base_url}/hledani/pronajem/{_KIND_URL[kind]}/{path}"
        params = [query] if query else []
        if kind == "byt":
            params.append("velikost=" + quote(",".join(_SIZE[d] for d in self.search.dispositions), safe=","))
        if page > 1:
            params.append(f"strana={page}")
        if params:
            url += "?" + "&".join(params)
        m = re.search(r'__NEXT_DATA__[^>]*>(.*?)</script>', self.get(url).text)
        if not m:
            raise RuntimeError("stránka neobsahuje __NEXT_DATA__ (změna webu?)")
        data = None
        for q in json.loads(m.group(1))["props"]["pageProps"]["dehydratedState"]["queries"]:
            if (q.get("queryKey") or [None])[0] == "estatesSearch":
                data = q["state"]["data"]
        if data is None:
            raise RuntimeError("chybí výsledky estatesSearch (změna webu?)")
        offers = []
        for it in data["results"]:
            loc = it["locality"]
            img = ("https:" + it["images"][0]["url"] + "?fl=res,800,600,3|shr,,20|jpg,80") if it.get("images") else ""
            offers.append(Offer(
                portal=self.name, link=self._link(it), title=it["name"], kind=kind, area_name=area.name,
                location=" - ".join(p for p in (loc.get("city"), loc.get("cityPart"), loc.get("street")) if p),
                price=it.get("priceCzk") or None, image_url=img))
        total = (data.get("pagination") or {}).get("total") or 0
        return offers, page * 20 < total
