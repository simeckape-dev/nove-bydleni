"""Spuštění: stahování nabídek na pozadí + webová stránka (python -m nove_bydleni)."""
import logging

import uvicorn

from .config import load_search, load_settings
from .runner import Runner
from .storage import Storage
from .web import create_app


def main():
    settings = load_settings()
    logging.basicConfig(level=logging.DEBUG if settings.debug else logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    search = load_search(settings.config_file)
    storage = Storage(settings.data_dir / "nabidky.db")
    runner = Runner(settings, search, storage)
    logging.info("Portály: %s; lokality: %s; typy: %s; dispozice: %s",
                 ", ".join(s.name for s in runner.scrapers), ", ".join(a.name for a in search.areas),
                 ", ".join(search.kinds), ", ".join(search.dispositions))
    runner.start()
    uvicorn.run(create_app(storage, runner), host=settings.listen, port=settings.port, log_level="warning",
                proxy_headers=True, forwarded_allow_ips="*")


if __name__ == "__main__":
    main()
