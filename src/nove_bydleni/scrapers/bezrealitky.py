"""BezRealitky.cz: GraphQL API. Lokalita = OSM relace (např. "R437354" = Ostrava)."""
import copy
import json
from pathlib import Path

from ..model import Offer
from .base import ScraperBase

_QUERY = json.loads((Path(__file__).parent / "bezrealitky.graphql.json").read_text())
_ESTATE = {"byt": "BYT", "dum": "DUM"}
_DISP = {"1+kk": "DISP_1_KK", "1+1": "DISP_1_1", "2+kk": "DISP_2_KK", "2+1": "DISP_2_1", "3+kk": "DISP_3_KK",
         "3+1": "DISP_3_1", "4+kk": "DISP_4_KK", "4+1": "DISP_4_1",
         "5+": ("DISP_5_KK", "DISP_5_1", "DISP_6_KK", "DISP_6_1", "DISP_7_KK", "DISP_7_1"), "atyp": "OSTATNI"}
_PAGE = 30


class Bezrealitky(ScraperBase):
    name = "BezRealitky"
    key = "bezrealitky"
    color = "#00906c"

    def fetch_page(self, kind, area, page):
        q = copy.deepcopy(_QUERY)
        disp = []
        if kind == "byt":
            for d in self.search.dispositions:
                v = _DISP[d]
                disp += list(v) if isinstance(v, tuple) else [v]
        q["variables"].update(estateType=_ESTATE[kind], offerType="PRONAJEM", disposition=disp,
                              regionOsmIds=[self.location_id(area)], limit=_PAGE, offset=(page - 1) * _PAGE)
        r = self.post("https://api.bezrealitky.cz/graphql/", json=q,
                      headers={"Origin": "https://www.bezrealitky.cz", "Referer": "https://www.bezrealitky.cz/"}).json()
        if r.get("errors"):
            raise RuntimeError(f"GraphQL: {str(r['errors'])[:200]}")
        data = r["data"]["listAdverts"]
        offers = []
        for it in data["list"]:
            price, charges = it.get("price"), it.get("charges")
            offers.append(Offer(
                portal=self.name, link=f"https://www.bezrealitky.cz/nemovitosti-byty-domy/{it['uri']}", kind=kind,
                area_name=area.name, title=it.get("imageAltText") or "", location=it.get("address") or "",
                price=price or None,
                price_text=f"{price:,} Kč + {charges:,} Kč poplatky".replace(",", " ") if price and charges else "",
                image_url=(it.get("mainImage") or {}).get("url", "")))
        return offers, page * _PAGE < (data.get("totalCount") or 0)
