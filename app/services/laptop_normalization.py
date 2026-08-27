import re

from app.models.normalized_laptop import NormalizedLaptop
from app.models.procurement_request import ProcurementRequest
from app.services.product_identity import extract_product_identity


def _normalize_text(value: str) -> str:
    """Collapse whitespace and use case-insensitive canonical text."""
    return " ".join(value.split()).casefold()


def _capacity_in_gb(value: str, field_name: str) -> int:
    match = re.search(r"(\d+(?:\.\d+)?)\s*(gb|tb)\b", value, re.IGNORECASE)
    if match is None:
        raise ValueError(f"{field_name} must include a capacity in GB or TB")

    capacity = float(match.group(1))
    if match.group(2).casefold() == "tb":
        capacity *= 1024

    if not capacity.is_integer():
        raise ValueError(f"{field_name} capacity must resolve to a whole number of GB")

    return int(capacity)


def _storage_type(value: str) -> str:
    normalized_value = _normalize_text(value)
    for storage_type in ("ssd", "hdd", "emmc"):
        if re.search(rf"\b{storage_type}\b", normalized_value):
            return storage_type
    return "unknown"


def normalize_laptop_request(request: ProcurementRequest) -> NormalizedLaptop:
    """Convert a validated laptop request into a consistent matching structure."""
    product_name = _normalize_text(request.product)
    identity = extract_product_identity(product_name)
    specifications = request.specifications
    cpu = _normalize_text(specifications.cpu) if specifications.cpu else None
    ram_gb = _capacity_in_gb(specifications.ram, "RAM") if specifications.ram else None
    storage_capacity_gb = (
        _capacity_in_gb(specifications.storage, "Storage")
        if specifications.storage
        else None
    )
    storage_type = _storage_type(specifications.storage) if specifications.storage else None

    missing_fields = [
        field_name
        for field_name in ("cpu", "ram", "storage")
        if getattr(specifications, field_name) is None
    ]
    analysis_readiness = "needs_more_information" if missing_fields else "ready"

    matching_key = "|".join(
        (
            product_name,
            cpu or "cpu:unknown",
            f"ram:{ram_gb}gb" if ram_gb is not None else "ram:unknown",
            (
                f"storage:{storage_capacity_gb}gb:{storage_type}"
                if storage_capacity_gb is not None
                else "storage:unknown"
            ),
            request.condition,
        )
    )

    return NormalizedLaptop(
        product_name=product_name,
        manufacturer=identity.manufacturer,
        product_line=identity.product_line,
        model_number=identity.model_number,
        cpu=cpu,
        ram_gb=ram_gb,
        storage_capacity_gb=storage_capacity_gb,
        storage_type=storage_type,
        condition=request.condition,
        missing_fields=missing_fields,
        analysis_readiness=analysis_readiness,
        matching_key=matching_key,
    )
