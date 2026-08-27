import json
import os
import time
from html.parser import HTMLParser
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from dotenv import load_dotenv

from app.models.market_observation_candidate import MarketObservationCandidate


load_dotenv()

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
        attributes = dict(attrs)
        if tag == "script" and attributes.get("type") == "application/ld+json":
            self._capturing = True
            self._buffer = []

    def handle_data(self, data: str) -> None:
        if self._capturing:
            self._buffer.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag != "script" or not self._capturing:
            return

        self._capturing = False
        try:
            self.documents.append(json.loads("".join(self._buffer)))
        except json.JSONDecodeError:
            pass
        self._buffer = []


def _find_product(document: Any) -> dict[str, Any] | None:
    if isinstance(document, dict):
        document_type = document.get("@type")
        if document_type == "Product" or (
            isinstance(document_type, list) and "Product" in document_type
        ):
            return document
        for value in document.values():
            product = _find_product(value)
            if product:
                return product
    elif isinstance(document, list):
        for value in document:
            product = _find_product(value)
            if product:
                return product
    return None


def extract_jumia_detail_metadata(html: str) -> tuple[str | None, str | None]:
    """Return seller and condition from a Jumia product's JSON-LD metadata."""
    parser = _JsonLdParser()
    parser.feed(html)

    product = next(
        (product for document in parser.documents if (product := _find_product(document))),
        None,
    )
    if product is None:
        return None, None

    offers = product.get("offers")
    if isinstance(offers, list):
        offers = offers[0] if offers else None
    if not isinstance(offers, dict):
        return None, None

    seller = offers.get("seller")
    supplier_name = seller.get("name") if isinstance(seller, dict) else None

    condition_value = str(offers.get("itemCondition", ""))
    condition_key = condition_value.rstrip("/").rsplit("/", maxsplit=1)[-1].casefold()
    condition = CONDITION_MAP.get(condition_key)
    return supplier_name, condition


def enrich_jumia_candidate_from_html(
    candidate: MarketObservationCandidate,
    html: str,
) -> MarketObservationCandidate:
    """Fill seller and condition from product metadata without overwriting facts."""
    supplier_name, condition = extract_jumia_detail_metadata(html)
    updates = {
        "supplier_name": candidate.supplier_name or supplier_name,
        "condition": candidate.condition or condition,
    }

    required_values = {
        "manufacturer": candidate.manufacturer,
        "model_number": candidate.model_number,
        "cpu": candidate.cpu,
        "ram": candidate.ram_gb,
        "storage": candidate.storage_capacity_gb,
        "condition": updates["condition"],
        "supplier": updates["supplier_name"],
        "source_external_id": candidate.raw_listing.source_external_id,
    }
    missing_fields = [name for name, value in required_values.items() if value is None]

    return candidate.model_copy(
        update={
            **updates,
            "missing_fields": missing_fields,
            "validation_status": "needs_enrichment" if missing_fields else "ready",
        }
    )


def enrich_jumia_candidate(
    candidate: MarketObservationCandidate,
) -> MarketObservationCandidate:
    """Fetch one product page and enrich its candidate from JSON-LD."""
    crawler_contact = os.getenv("CRAWLER_CONTACT")
    if not crawler_contact:
        raise RuntimeError("CRAWLER_CONTACT is not configured")

    request = Request(
        candidate.raw_listing.source_url,
        headers={
            "User-Agent": f"ProcurementIntelligenceBot/0.1 (+{crawler_contact})"
        },
    )
    with urlopen(request, timeout=15) as response:
        html = response.read().decode("utf-8", errors="replace")
    return enrich_jumia_candidate_from_html(candidate, html)


def enrich_jumia_candidates(
    candidates: list[MarketObservationCandidate],
) -> list[MarketObservationCandidate]:
    """Enrich candidates sequentially while keeping request frequency conservative."""
    enriched: list[MarketObservationCandidate] = []
    for index, candidate in enumerate(candidates):
        if index:
            time.sleep(2)
        try:
            enriched.append(enrich_jumia_candidate(candidate))
        except (HTTPError, URLError, TimeoutError):
            enriched.append(candidate)
    return enriched
