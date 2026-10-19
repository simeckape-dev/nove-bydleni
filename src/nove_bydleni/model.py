"""Nabídka nemovitosti a pomocné funkce pro dispozice a ceny."""
import re
from dataclasses import dataclass, field

# Dispozice, které jde zadat v konfiguraci. "5+" = 5+kk a víc, "atyp" = atypické nebo neznámé.
DISPOSITIONS = ("1+kk", "1+1", "2+kk", "2+1", "3+kk", "3+1", "4+kk", "4+1", "5+", "atyp")

KINDS = ("byt", "dum")

_DISP_RE = re.compile(r"(?<![\d.,])(\d)\s*\+\s*(kk|1|k\.k\.)(?![\d])", re.IGNORECASE)
_AREA_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*m(?:²|2)", re.IGNORECASE)


def parse_disposition(text: str) -> str | None:
    """Dispozice z textu nabídky ("Pronájem bytu 2+kk 54 m²" -> "2+kk"), None když v textu není."""
    if not text:
        return None
    m = _DISP_RE.search(text)
    if not m:
        return "atyp" if re.search(r"atyp", text, re.IGNORECASE) else None
    rooms, suffix = int(m.group(1)), m.group(2).lower()
    if rooms >= 5:
        return "5+"
    return f"{rooms}+{'1' if suffix == '1' else 'kk'}"


def parse_area(text: str) -> int | None:
    """Užitná plocha v m² z textu, první výskyt."""
    m = _AREA_RE.search(text or "")
    return round(float(m.group(1).replace(",", "."))) if m else None


def parse_price(value) -> int | None:
    """Cena jako celé číslo Kč; text bez čísel (např. "Cena na dotaz") -> None."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return int(value) or None
    digits = re.sub(r"[^\d]", "", str(value).split("/")[0].split("+")[0])
    return int(digits) if digits else None


@dataclass
class Offer:
    """Jedna nabídka z realitního serveru."""

    portal: str
    """Název portálu (např. "Sreality")"""
    link: str
    """Adresa nabídky, slouží i jako jednoznačný klíč"""
    title: str
    location: str
    """Adresa nebo čtvrť, jak ji uvádí portál"""
    kind: str
    """"byt" nebo "dum\""""
    area_name: str
    """Lokalita z konfigurace, pro kterou byla nabídka nalezena (např. "Ostrava")"""
    price: int | None = None
    """Nájem za měsíc v Kč (bez poplatků, pokud je portál uvádí zvlášť)"""
    price_text: str = ""
    """Cena tak, jak ji portál zobrazuje (s poplatky, "na dotaz" apod.)"""
    image_url: str = ""
    disposition: str | None = None
    surface: int | None = None
    extra: dict = field(default_factory=dict)

    def __post_init__(self):
        if self.disposition is None:
            self.disposition = parse_disposition(self.title)
        if self.surface is None:
            self.surface = parse_area(self.title)
        if not self.price_text and self.price:
            self.price_text = f"{self.price:,} Kč".replace(",", " ")
