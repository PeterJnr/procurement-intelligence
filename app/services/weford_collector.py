import hashlib
import json
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

DEFAULT_WEFORD_URL = (
    "https://www.wefordenterprise.com/shop/dell-latitude-5440-i5-touch"
)


class ProductUnavailableError(ValueError):
    """Raised when a configured product page is not currently in stock."""


class _PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.documents: list[Any] = []
        self.headings: list[str] = []
        self._json_buffer: list[str] | None = None
        self._heading_buffer: list[str] | None = None

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        attributes = dict(attrs)
        if tag == "script" and attributes.get("type") == "application/ld+json":
            self._json_buffer = []
        if tag == "h1":
            self._heading_buffer = []

    def handle_data(self, data: str) -> None:
        value = " ".join(data.split())
        if value:
            self.parts.append(value)
        if self._json_buffer is not None:
            self._json_buffer.append(data)
        if self._heading_buffer is not None:
            self._heading_buffer.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "script" and self._json_buffer is not None:
            try:
                self.documents.append(json.loads("".join(self._json_buffer)))
            except json.JSONDecodeError:
                pass
            self._json_buffer = None
        if tag == "h1" and self._heading_buffer is not None:
            heading = " ".join("".join(self._heading_buffer).split())
            if heading:
                self.headings.append(heading)
            self._heading_buffer = None


def _find_product(value: Any) -> dict[str, Any] | None:
    if isinstance(value, dict):
        product_type = value.get("@type")
        if product_type == "Product" or (
            isinstance(product_type, list) and "Product" in product_type
        ):
            return value
        for nested in value.values():
            if product := _find_product(nested):
                return product
    elif isinstance(value, list):
        for nested in value:
            if product := _find_product(nested):
                return product
    return None


def _offer(product: dict[str, Any]) -> dict[str, Any]:
    offers = product.get("offers")
    if isinstance(offers, list):
        offers = next((item for item in offers if isinstance(item, dict)), None)
    return offers if isinstance(offers, dict) else {}


def _label_value(text: str, label: str, following_label: str) -> str | None:
    match = re.search(
        rf"\b{label}\b\s+(.+?)\s+\b{following_label}\b",
        text,
        re.IGNORECASE,
    )
    return match.group(1).strip() if match else None


def parse_weford_product(
    html: str,
    source_url: str,
    collected_at: datetime | None = None,
) -> MarketObservationCandidate:
    """Parse one explicitly configured, currently available WeFord page."""
    parser = _PageParser()
    parser.feed(html)
    text = " ".join(parser.parts)
    product = next(
        (item for document in parser.documents if (item := _find_product(document))),
        {},
    )
    offer = _offer(product)

    availability = str(offer.get("availability", ""))
    explicitly_in_stock = bool(
        re.search(r"\bin stock\b", text, re.IGNORECASE)
        or availability.rstrip("/").casefold().endswith("instock")
    )
    explicitly_out_of_stock = bool(
        re.search(r"\bout of stock\b", text, re.IGNORECASE)
        or availability.rstrip("/").casefold().endswith("outofstock")
    )
    if explicitly_out_of_stock or not explicitly_in_stock:
        raise ProductUnavailableError("WeFord product is not confirmed in stock")

    title = str(product.get("name") or (parser.headings[0] if parser.headings else ""))
    processor = _label_value(text, "Processor", "Memory")
    memory = _label_value(text, "Memory", "Storage")
    storage = _label_value(text, "Storage", "Operating System")
    enriched_title = " ".join(value for value in (title, processor, memory, storage) if value)

    price_value = offer.get("price")
    if price_value is None:
        price_match = re.search(r"₦\s*([\d,]+(?:\.\d+)?)", text)
        if not price_match:
            raise ValueError("WeFord product price was not found")
        price_value = price_match.group(1).replace(",", "")

    external_id = str(product.get("sku") or "") or hashlib.sha256(
        source_url.encode("utf-8")
    ).hexdigest()[:32]
    listing = CollectedMarketListing(
        title=enriched_title,
        unit_price=Decimal(str(price_value)),
        currency="NGN",
        source_name="WeFord Enterprise",
        source_url=source_url,
        source_external_id=external_id,
        collected_at=collected_at or datetime.now(timezone.utc),
    )
    candidate = extract_listing_candidate(listing)
    required = {
        "manufacturer": candidate.manufacturer,
        "model_number": candidate.model_number,
        "cpu": candidate.cpu,
        "ram": candidate.ram_gb,
        "storage": candidate.storage_capacity_gb,
        "source_external_id": external_id,
    }
    missing_fields = [name for name, value in required.items() if value is None]
    return candidate.model_copy(
        update={
            "condition": "new",
            "supplier_name": "WeFord Enterprise",
            "missing_fields": missing_fields,
            "validation_status": "needs_enrichment" if missing_fields else "ready",
        }
    )


def configured_weford_urls() -> list[str]:
    value = os.getenv("WEFORD_PRODUCT_URLS", DEFAULT_WEFORD_URL)
    return [url.strip() for url in value.split(",") if url.strip()]


def collect_weford_candidates() -> list[MarketObservationCandidate]:
    crawler_contact = os.getenv("CRAWLER_CONTACT")
    if not crawler_contact:
        raise RuntimeError("CRAWLER_CONTACT is not configured")

    candidates = []
    for source_url in configured_weford_urls():
        request = Request(
            source_url,
            headers={
                "User-Agent": f"ProcurementIntelligenceBot/0.1 (+{crawler_contact})"
            },
        )
        with urlopen(request, timeout=20) as response:
            html = response.read().decode("utf-8", errors="replace")
        try:
            candidates.append(parse_weford_product(html, source_url))
        except ProductUnavailableError:
            continue
    return candidates
