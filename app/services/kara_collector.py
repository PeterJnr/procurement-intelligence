import hashlib
import os
import re
from datetime import datetime, timezone
from decimal import Decimal
from html.parser import HTMLParser
from typing import Any
from urllib.request import Request, urlopen

from dotenv import load_dotenv

from app.models.collected_market_listing import CollectedMarketListing
from app.models.market_observation_candidate import MarketObservationCandidate
from app.services.listing_extraction import extract_listing_candidate


load_dotenv()

DEFAULT_KARA_URL = (
    "https://kara.com.ng/"
    "dell-latitude-5440-laptop-intel-core-i5-1345u-pn-lat5440cto"
)
CONDITION_MAP = {
    "newcondition": "new",
    "usedcondition": "used",
    "refurbishedcondition": "refurbished",
}


class _JsonLdParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.documents: list[Any] = []
        self._capturing = False
        self._buffer: list[str] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        if tag == "script" and dict(attrs).get("type") == "application/ld+json":
            self._capturing = True
            self._buffer = []

    def handle_data(self, data: str) -> None:
        if self._capturing:
            self._buffer.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "script" and self._capturing:
            import json

            self._capturing = False
            try:
                self.documents.append(json.loads("".join(self._buffer)))
            except json.JSONDecodeError:
                pass


class _TextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        value = " ".join(data.split())
        if value:
            self.parts.append(value)


def _find_product(value: Any) -> dict[str, Any] | None:
    if isinstance(value, dict):
        if value.get("@type") == "Product":
            return value
        for nested in value.values():
            if product := _find_product(nested):
                return product
    elif isinstance(value, list):
        for nested in value:
            if product := _find_product(nested):
                return product
    return None


def _page_text(html: str) -> str:
    parser = _TextParser()
    parser.feed(html)
    return " ".join(parser.parts)


def parse_kara_product(
    html: str,
    source_url: str,
    collected_at: datetime | None = None,
) -> MarketObservationCandidate:
    """Parse and validate one explicitly configured Kara product page."""
    parser = _JsonLdParser()
    parser.feed(html)
    product = next(
        (item for document in parser.documents if (item := _find_product(document))),
        None,
    )
    if product is None:
        raise ValueError("Kara product metadata was not found")

    offers = product.get("offers")
    if not isinstance(offers, dict):
        raise ValueError("Kara offer metadata was not found")

    text = _page_text(html)
    ram_match = re.search(r"\bRAM\s+(\d+)\s*GB\b", text, re.IGNORECASE)
    storage_match = re.search(
        r"\bStorage\s+(\d+)\s*(GB|TB).*?\b(SSD|HDD|eMMC)\b",
        text,
        re.IGNORECASE,
    )
    title = str(product.get("name", ""))
    if ram_match:
        title += f" {ram_match.group(1)}GB RAM"
    if storage_match:
        title += " " + " ".join(storage_match.groups())

    seller = offers.get("seller")
    supplier = seller.get("name") if isinstance(seller, dict) else None
    condition_key = str(offers.get("itemCondition", "")).rstrip("/").rsplit("/", 1)[-1]
    condition = CONDITION_MAP.get(condition_key.casefold())
    external_id = str(product.get("sku") or "") or hashlib.sha256(
        source_url.encode("utf-8")
    ).hexdigest()[:32]

    listing = CollectedMarketListing(
        title=title,
        unit_price=Decimal(str(offers["price"])),
        currency="NGN",
        source_name="Kara Nigeria",
        source_url=source_url,
        source_external_id=external_id,
        collected_at=collected_at or datetime.now(timezone.utc),
    )
    candidate = extract_listing_candidate(listing)
    updates = {
        "supplier_name": supplier,
        "condition": condition,
    }
    required = {
        "manufacturer": candidate.manufacturer,
        "model_number": candidate.model_number,
        "cpu": candidate.cpu,
        "ram": candidate.ram_gb,
        "storage": candidate.storage_capacity_gb,
        "condition": condition,
        "supplier": supplier,
        "source_external_id": external_id,
    }
    missing_fields = [name for name, value in required.items() if value is None]
    return candidate.model_copy(
        update={
            **updates,
            "missing_fields": missing_fields,
            "validation_status": "needs_enrichment" if missing_fields else "ready",
        }
    )


def configured_kara_urls() -> list[str]:
    value = os.getenv("KARA_PRODUCT_URLS", DEFAULT_KARA_URL)
    return [url.strip() for url in value.split(",") if url.strip()]


def collect_kara_candidates() -> list[MarketObservationCandidate]:
    crawler_contact = os.getenv("CRAWLER_CONTACT")
    if not crawler_contact:
        raise RuntimeError("CRAWLER_CONTACT is not configured")

    candidates = []
    for source_url in configured_kara_urls():
        request = Request(
            source_url,
            headers={
                "User-Agent": f"ProcurementIntelligenceBot/0.1 (+{crawler_contact})"
            },
        )
        with urlopen(request, timeout=20) as response:
            html = response.read().decode("utf-8", errors="replace")
        candidates.append(parse_kara_product(html, source_url))
    return candidates
