# Nové bydlení

Hlídá nabídky **pronájmu bytů a domů** na českých realitních portálech a zobrazuje je na vlastní webové stránce
(karty s fotkou, cenou a odkazy, filtry, označení nových, zlevněných a zmizelých nabídek, stav portálů).

Fork projektu [janchaloupka/web-scraper-nabidek-pronajmu](https://github.com/janchaloupka/web-scraper-nabidek-pronajmu)
(původně pronájmy bytů v Brně s výstupem do Discordu). Změny oproti originálu:

- hledání (typy, dispozice, lokality) v jednom souboru YAML, každý portál má vlastní identifikátor lokality;
- místo Discordu webová stránka a historie v SQLite (první výskyt, změny ceny, zmizení z portálu);
- stránkování (celá nabídka, ne jen první stránka), byty i domy;
- stejná nemovitost z více portálů se zobrazí jako jedna karta s odkazy na všechny;
- nové portály Reality.cz a M&M Reality, zpět realingo; BRAVIS (jen Brno) odstraněn.

## Portály

Sreality, iDNES Reality, BezRealitky, realingo, UlovDomov, RE/MAX, REALCITY, EuroBydlení, Reality.cz, M&M Reality.

RE/MAX, REALCITY, EuroBydlení a M&M Reality umí hledat jen v okrese nebo v obdélníku na mapě, proto se jejich
nabídky navíc filtrují podle `obce` lokality.

## Konfigurace hledání

Soubor `config/hledani.yaml` (cesta v `CONFIG_FILE`), viz komentáře v souboru. Lokalita má pro každý portál
vlastní identifikátor; chybí-li, portál se pro ni přeskočí.

## Proměnné prostředí

| Proměnná | Výchozí | Význam |
|---|---|---|
| `CONFIG_FILE` | `config/hledani.yaml` | soubor s hledáním |
| `DATA_DIR` | `data` | adresář pro databázi `nabidky.db` |
| `PORT` / `LISTEN` | `8080` / `0.0.0.0` | webová stránka |
| `REFRESH_INTERVAL_DAYTIME_MINUTES` | `30` | interval stahování 6–22 h |
| `REFRESH_INTERVAL_NIGHTTIME_MINUTES` | `90` | interval stahování v noci |
| `DEBUG` | `0` | podrobný výpis |

První stažení nabídky jen uloží (nejsou označené jako nové), nové jsou až ty, které přibudou potom.

## Spuštění

```sh
pip install -r requirements.txt
PYTHONPATH=src python -m nove_bydleni      # http://localhost:8080
```

Image `ghcr.io/simeckape-dev/nove-bydleni` (amd64, arm64) sestavuje GitHub Actions při pushi do `master`.

Stránka nemá přihlášení, patří jen do domácí sítě.
