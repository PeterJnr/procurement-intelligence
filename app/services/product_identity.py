import re

from app.models.product_identity import ProductIdentity


KNOWN_MANUFACTURERS = {
    "dell": "dell",
    "hp": "hp",
    "hewlett packard": "hp",
    "lenovo": "lenovo",
}
KNOWN_PRODUCT_LINES = ("latitude", "elitebook", "probook", "thinkpad")
MODEL_TOKEN = re.compile(r"^[a-z]?\d{2,5}[a-z0-9-]*$")


def extract_product_identity(product_name: str) -> ProductIdentity:
    """Extract only recognizable identity tokens without guessing."""
    normalized = " ".join(
        re.sub(r"[^a-z0-9]+", " ", product_name.casefold()).split()
    )
    tokens = normalized.split()

    manufacturer = next(
        (
            canonical
            for name, canonical in KNOWN_MANUFACTURERS.items()
            if re.search(rf"\b{re.escape(name)}\b", normalized)
        ),
        None,
    )
    product_line = next(
        (line for line in KNOWN_PRODUCT_LINES if line in tokens),
        None,
    )

    model_number = None
    if product_line is not None:
        line_index = tokens.index(product_line)
        adjacent_tokens = []
        if line_index + 1 < len(tokens):
            adjacent_tokens.append(tokens[line_index + 1])
        if line_index > 0:
            adjacent_tokens.append(tokens[line_index - 1])
        model_number = next(
            (token for token in adjacent_tokens if MODEL_TOKEN.fullmatch(token)),
            None,
        )

    return ProductIdentity(
        manufacturer=manufacturer,
        product_line=product_line,
        model_number=model_number,
    )

