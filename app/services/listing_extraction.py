import re

from app.models.collected_market_listing import CollectedMarketListing
from app.models.market_observation_candidate import MarketObservationCandidate


KNOWN_PRODUCT_LINES = ("latitude", "elitebook", "probook", "thinkpad")
KNOWN_MANUFACTURERS = {
    "dell": "dell",
    "hp": "hp",
    "lenovo": "lenovo",
}


def _capacity_in_gb(amount: str, unit: str) -> int:
    capacity = int(amount)
    return capacity * 1024 if unit.casefold() == "tb" else capacity


def extract_listing_candidate(
    listing: CollectedMarketListing,
) -> MarketObservationCandidate:
    """Extract explicit laptop attributes without guessing absent information."""
    title = " ".join(listing.title.split())
    normalized_title = title.casefold()
    searchable_title = re.sub(r"[^\w-]+", " ", normalized_title)

    manufacturer = next(
        (
            canonical_name
            for token, canonical_name in KNOWN_MANUFACTURERS.items()
            if re.search(rf"\b{re.escape(token)}\b", searchable_title)
        ),
        None,
    )

    product_line = next(
        (
            line
            for line in KNOWN_PRODUCT_LINES
            if re.search(rf"\b{line}\b", searchable_title)
        ),
        None,
    )

    model_number = None
    if product_line:
        model_match = re.search(
            rf"\b{re.escape(product_line)}\s+([a-z]?\d{{2,5}}[a-z0-9-]*)\b",
            searchable_title,
        )
        if model_match:
            model_number = model_match.group(1)

    cpu_match = re.search(
        r"\b(intel\s+(?:core\s+)?i[3579](?:-[a-z0-9]+)?)\b",
        searchable_title,
    )
    cpu = " ".join(cpu_match.group(1).split()) if cpu_match else None

    ram_match = re.search(r"\b(\d+)\s*gb\s+(?:ddr\d\s+)?ram\b", searchable_title)
    ram_gb = int(ram_match.group(1)) if ram_match else None

    storage_match = re.search(
        r"\b(\d+)\s*(gb|tb)\s+(ssd|hdd|emmc)\b",
        searchable_title,
    )
    storage_capacity_gb = (
        _capacity_in_gb(storage_match.group(1), storage_match.group(2))
        if storage_match
        else None
    )
    storage_type = storage_match.group(3) if storage_match else None

    condition = None
    if re.search(r"\b(?:refurbished|renewed)\b", searchable_title):
        condition = "refurbished"
    elif re.search(r"\bused\b", searchable_title):
        condition = "used"
    elif re.search(r"\bnew\b", searchable_title):
        condition = "new"

    required_fields = {
        "manufacturer": manufacturer,
        "model_number": model_number,
        "cpu": cpu,
        "ram": ram_gb,
        "storage": storage_capacity_gb,
        "condition": condition,
        "supplier": None,
        "source_external_id": listing.source_external_id,
    }
    missing_fields = [
        field_name for field_name, value in required_fields.items() if value is None
    ]

    return MarketObservationCandidate(
        raw_listing=listing,
        manufacturer=manufacturer,
        product_line=product_line,
        model_number=model_number,
        cpu=cpu,
        ram_gb=ram_gb,
        storage_capacity_gb=storage_capacity_gb,
        storage_type=storage_type,
        condition=condition,
        supplier_name=None,
        missing_fields=missing_fields,
        validation_status="needs_enrichment" if missing_fields else "ready",
    )


def extract_listing_candidates(
    listings: list[CollectedMarketListing],
) -> list[MarketObservationCandidate]:
    return [extract_listing_candidate(listing) for listing in listings]
