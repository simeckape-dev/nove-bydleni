"""UlovDomov.cz: API hledání v mapě. Lokalita = hranice [sever, východ, jih, západ]."""
from ..model import Offer
from .base import ScraperBase

_DISP = {"1+kk": 2, "1+1": 3, "2+kk": 4, "2+1": 5, "3+kk": 6, "3+1": 7, "4+kk": 8, "4+1": 9,
         "5+": (10, 11, 12, 13, 14, 15), "atyp": 16}
_DISP_NAME = {1: "garsoniéra", 2: "1+kk", 3: "1+1", 4: "2+kk", 5: "2+1", 6: "3+kk", 7: "3+1", 8: "4+kk", 9: "4+1",
              10: "5+kk", 11: "5+1", 12: "6+kk", 13: "6+1", 14: "7+kk", 15: "7+1", 16: "atypický", 29: "dům"}
_HOUSE = 29
_PAGE = 20


class UlovDomov(ScraperBase):
    name = "UlovDomov"
    key = "ulovdomov"
    color = "#f5a623"

    def fetch_page(self, kind, area, page):
        north, east, south, west = self.location_id(area)
        if kind == "byt":
            disp = []
            for d in self.search.dispositions:
                v = _DISP[d]
                disp += list(v) if isinstance(v, tuple) else [v]
        else:
            disp = [_HOUSE]
        req = {"acreage_from": "", "acreage_to": "", "added_before": "", "banner_panel_width_type": 480,
               "bounds": {"north_east": {"lat": north, "lng": east}, "south_west": {"lat": south, "lng": west}},
               "conveniences": [], "dispositions": disp, "furnishing": [], "is_price_commision_free": None,
               "limit": _PAGE, "offer_type_id": None, "page": page, "price_from": "", "price_to": "", "query": "",
               "sort_by": "date:desc", "sticker": None}
        r = self.post("https://www.ulovdomov.cz/fe-api/find/seperated-offers-within-bounds", json=req).json()
        offers = []
        for it in r.get("offers", []):
            loc = it["village"]["label"]
            if it.get("street"):
                loc = it["street"]["label"] + ", " + loc
            if it.get("village_part"):
                loc += " - " + it["village_part"]["label"]
            what = "domu" if it.get("disposition_id") == _HOUSE else _DISP_NAME.get(it.get("disposition_id"), "")
            offers.append(Offer(
                portal=self.name, link=it["absolute_url"], kind=kind, area_name=area.name,
                title=f"Pronájem {what} {it.get('acreage') or ''} m²".replace("  ", " "), location=loc,
                price=it.get("price_rental") or None,
                image_url=(it.get("photos") or [{}])[0].get("path", "")))
        return offers, page * _PAGE < (r.get("count") or 0)
