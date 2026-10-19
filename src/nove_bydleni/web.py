"""Webová stránka s nabídkami a stavem portálů."""
import json
import time
from collections import OrderedDict
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from .model import DISPOSITIONS
from .runner import Runner
from .storage import Storage

NEW_HOURS = 48
KIND_NAMES = {"byt": "Byt", "dum": "Dům"}


SURFACE_TOLERANCE = 2


def _group(rows) -> "OrderedDict[tuple, dict]":
    """Stejná nemovitost na více portálech: shoda typu, lokality, dispozice a ceny, plocha ± SURFACE_TOLERANCE m²."""
    groups: "OrderedDict[tuple, dict]" = OrderedDict()
    buckets: dict[tuple, list[tuple]] = {}
    for o in rows:
        key = (o["link"],)
        if o["surface"] and o["price"]:
            bucket = buckets.setdefault((o["kind"], o["area_name"], o["disposition"], o["price"]), [])
            key = next((k for k in bucket if abs(k[-1] - o["surface"]) <= SURFACE_TOLERANCE), None)
            if key is None:
                key = (o["kind"], o["area_name"], o["disposition"], o["price"], o["surface"])
                bucket.append(key)
        g = groups.setdefault(key, {"main": o, "links": [], "first_seen": o["first_seen"]})
        if o["portal"] not in [l["portal"] for l in g["links"]]:
            g["links"].append({"portal": o["portal"], "link": o["link"]})
        g["first_seen"] = min(g["first_seen"], o["first_seen"])
        if not g["main"]["image_url"] and o["image_url"]:
            g["main"] = o
    return groups


def create_app(storage: Storage, runner: Runner) -> FastAPI:
    app = FastAPI(title="Nové bydlení", docs_url=None, redoc_url=None)
    templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
    templates.env.filters["czk"] = lambda v: f"{v:,} Kč".replace(",", " ") if v else ""
    templates.env.filters["dt"] = lambda t: time.strftime("%-d. %-m. %H:%M", time.localtime(t)) if t else "–"

    @app.get("/", response_class=HTMLResponse)
    def index(request: Request, typ: str = "", lokalita: str = "", portal: str = "", dispozice: str = "",
              cena_do: str = "", jen_nove: str = "", zmizele: str = "", razeni: str = "nove"):
        # Formulář posílá i prázdná pole (cena_do=), proto parametry jako text
        now = time.time()
        cena_do = int(cena_do) if cena_do.strip().isdigit() else None
        jen_nove = 1 if jen_nove else 0
        zmizele = 1 if zmizele else 0
        groups = _group(storage.offers(include_gone=bool(zmizele)))
        disps = [d for d in dispozice.split(",") if d]
        items = []
        for g in groups.values():
            o = g["main"]
            if typ and o["kind"] != typ or lokalita and o["area_name"] != lokalita:
                continue
            if portal and portal not in [l["portal"] for l in g["links"]]:
                continue
            if disps and o["disposition"] not in disps:
                continue
            if cena_do and (not o["price"] or o["price"] > cena_do):
                continue
            is_new = not o["silent"] and now - g["first_seen"] < NEW_HOURS * 3600
            if jen_nove and not is_new:
                continue
            history = json.loads(o["price_history"])
            items.append({"o": o, "links": g["links"], "first_seen": g["first_seen"], "new": is_new,
                          "cheaper": bool(history and history[-1]["new"] < history[-1]["old"]), "history": history})
        if razeni == "cena":
            items.sort(key=lambda i: i["o"]["price"] or 10**9)
        elif razeni == "plocha":
            items.sort(key=lambda i: -(i["o"]["surface"] or 0))
        else:
            items.sort(key=lambda i: -i["first_seen"])
        return templates.TemplateResponse(request, "index.html", {
            "items": items, "count_all": len(groups), "kinds": KIND_NAMES,
            "areas": [a.name for a in runner.search.areas], "portals": [s.name for s in runner.scrapers],
            "dispositions": [d for d in DISPOSITIONS if d in runner.search.dispositions],
            "f": {"typ": typ, "lokalita": lokalita, "portal": portal, "dispozice": disps, "cena_do": cena_do or "",
                  "jen_nove": jen_nove, "zmizele": zmizele, "razeni": razeni},
            "runner": runner, "new_hours": NEW_HOURS})

    @app.get("/stav", response_class=HTMLResponse)
    def status(request: Request):
        return templates.TemplateResponse(request, "status.html", {"runs": storage.runs(), "runner": runner,
                                                                   "kinds": KIND_NAMES})

    @app.post("/stav/spustit")
    def run_now():
        runner.run_now()
        return RedirectResponse("/stav", status_code=303)

    @app.get("/healthz")
    def healthz():
        return JSONResponse({"ok": True, "running": runner.running, "last_cycle": runner.last_cycle})

    return app
