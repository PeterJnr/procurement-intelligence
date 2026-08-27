import os
import re
from datetime import datetime, timezone
from decimal import Decimal
from html.parser import HTMLParser
from urllib.parse import urljoin
from urllib.request import Request, urlopen

from dotenv import load_dotenv

from app.models.collected_market_listing import CollectedMarketListing
from app.models.market_observation_candidate import MarketObservationCandidate
from app.services.listing_extraction import extract_listing_candidates
from app.services.jumia_enrichment import enrich_jumia_candidates


JUMIA_BASE_URL = "https://www.jumia.com.ng"

load_dotenv()


class _JumiaListingParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.listings: list[dict[str, str]] = []
        self._current: dict[str, str] | None = None
        self._capture: str | None = None

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        attributes = dict(attrs)
        classes = set((attributes.get("class") or "").split())

        if tag == "article" and "prd" in classes:
            self._current = {}
        elif self._current is not None and tag == "a" and "core" in classes:
            if attributes.get("href"):
                self._current["url"] = attributes["href"]
        elif self._current is not None and tag == "h3" and "name" in classes:
            self._capture = "title"
            self._current[self._capture] = ""
        elif self._current is not None and tag == "div" and "prc" in classes:
            self._capture = "price"
            self._current[self._capture] = ""

    def handle_data(self, data: str) -> None:
        if self._current is not None and self._capture is not None:
            self._current[self._capture] += data

    def handle_endtag(self, tag: str) -> None:
        if tag in {"h3", "div"}:
            self._capture = None
        elif tag == "article" and self._current is not None:
            if {"title", "price", "url"}.issubset(self._current):
                self.listings.append(self._current)
            self._current = None
            self._capture = None


def _product_catalogue_url(product_name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", product_name.casefold()).strip("-")
    if not slug:
        raise ValueError("Product name cannot be converted into a catalogue URL")
    return f"{JUMIA_BASE_URL}/mlp-{slug}/"


def _parse_ngn_price(value: str) -> Decimal:
    match = re.search(r"[\d,]+(?:\.\d{1,2})?", value)
    if match is None:
        raise ValueError(f"Could not parse NGN price: {value}")
    return Decimal(match.group(0).replace(",", ""))


def _source_external_id(url: str) -> str | None:
    match = re.search(r"-(\d+)\.html(?:\?.*)?$", url)
    return match.group(1) if match else None


def parse_jumia_listings(
    html: str,
    collected_at: datetime | None = None,
) -> list[CollectedMarketListing]:
    """Parse listing cards from a Jumia catalogue page."""
    parser = _JumiaListingParser()
    parser.feed(html)
    timestamp = collected_at or datetime.now(timezone.utc)

    listings = []
    for item in parser.listings:
        source_url = urljoin(JUMIA_BASE_URL, item["url"])
        listings.append(
            CollectedMarketListing(
                title=" ".join(item["title"].split()),
                unit_price=_parse_ngn_price(item["price"]),
                source_url=source_url,
                source_external_id=_source_external_id(source_url),
                collected_at=timestamp,
            )
        )
    return listings


def collect_jumia_listings(product_name: str) -> list[CollectedMarketListing]:
    """Fetch one permitted Jumia catalogue page and return its raw listings."""
    crawler_contact = os.getenv("CRAWLER_CONTACT")
    if not crawler_contact:
        raise RuntimeError("CRAWLER_CONTACT is not configured")

    request = Request(
        _product_catalogue_url(product_name),
        headers={
            "User-Agent": (
                f"ProcurementIntelligenceBot/0.1 (+{crawler_contact})"
            )
        },
    )
    with urlopen(request, timeout=15) as response:
        html = response.read().decode("utf-8", errors="replace")

    return parse_jumia_listings(html)


def collect_jumia_candidates(
    product_name: str,
) -> list[MarketObservationCandidate]:
    """Collect raw listings and pass them through the validation gate."""
    return extract_listing_candidates(collect_jumia_listings(product_name))


def collect_and_enrich_jumia_candidates(
    product_name: str,
) -> list[MarketObservationCandidate]:
    """Collect listings and enrich them from their individual product pages."""
    return enrich_jumia_candidates(collect_jumia_candidates(product_name))
