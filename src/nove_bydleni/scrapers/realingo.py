"""realingo.cz: GraphQL API (sbírá nabídky i z dalších serverů). Lokalita = adresa, např. "Ostrava"."""
from ..model import Offer
from .base import ScraperBase

_QUERY = """query SearchOffer($purpose: OfferPurpose, $property: PropertyType, $categories: [OfferCategory!], $address: String,
 $sort: OfferSort = NEWEST, $first: Int = 100, $skip: Int = 0) {
  searchOffer(filter: {purpose: $purpose, property: $property, address: $address, categories: $categories},
              sort: $sort, first: $first, skip: $skip, save: false) {
    total
    items { id url category price { total } area { main } photos { main } location { address } }
  }
}"""
_PROPERTY = {"byt": "FLAT", "dum": "HOUSE"}
_CAT = {"1+kk": "FLAT1_KK", "1+1": "FLAT11", "2+kk": "FLAT2_KK", "2+1": "FLAT21", "3+kk": "FLAT3_KK", "3+1": "FLAT31",
        "4+kk": "FLAT4_KK", "4+1": "FLAT41", "5+": ("FLAT5_KK", "FLAT51", "FLAT6_AND_MORE"), "atyp": "OTHERS_FLAT"}
_CAT_NAME = {"FLAT1_KK": "1+kk", "FLAT11": "1+1", "FLAT2_KK": "2+kk", "FLAT21": "2+1", "FLAT3_KK": "3+kk",
             "FLAT31": "3+1", "FLAT4_KK": "4+kk", "FLAT41": "4+1", "FLAT5_KK": "5+kk", "FLAT51": "5+1",
             "FLAT6_AND_MORE": "6+", "HOUSE_FAMILY": "rodinný dům", "HOUSE_MANSION": "vila", "OTHERS_FLAT": "atypický"}
_PAGE = 100


class Realingo(ScraperBase):
    name = "realingo"
    key = "realingo"
    color = "#00bfa5"

    def fetch_page(self, kind, area, page):
        variables = {"purpose": "RENT", "property": _PROPERTY[kind], "address": self.location_id(area),
                     "sort": "NEWEST", "first": _PAGE, "skip": (page - 1) * _PAGE}
        if kind == "byt":
            cats = []
            for d in self.search.dispositions:
                v = _CAT[d]
                cats += list(v) if isinstance(v, tuple) else [v]
            variables["categories"] = cats
        r = self.post("https://www.realingo.cz/graphql",
                      json={"query": _QUERY, "operationName": "SearchOffer", "variables": variables}).json()
        if r.get("errors"):
            raise RuntimeError(f"GraphQL: {str(r['errors'])[:200]}")
        data = r["data"]["searchOffer"]
        offers = []
        for it in data["items"]:
            cat = _CAT_NAME.get(it["category"], "")
            surface = (it.get("area") or {}).get("main")
            title = " ".join(p for p in ("Pronájem bytu" if kind == "byt" else "Pronájem domu", cat,
                                         f"{surface} m²" if surface else "") if p)
            photo = (it.get("photos") or {}).get("main")
            offers.append(Offer(
                portal=self.name, link=f"https://www.realingo.cz{it['url']}", kind=kind, area_name=area.name,
                title=title, location=(it.get("location") or {}).get("address") or "",
                price=(it.get("price") or {}).get("total"), surface=surface,
                image_url=f"https://www.realingo.cz/image/{photo}/400x300" if photo else ""))
        return offers, page * _PAGE < (data.get("total") or 0)
