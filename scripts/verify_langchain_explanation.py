import json

from dotenv import load_dotenv

from app.services.analysis_explanation import build_explanation_chain


def main() -> None:
    load_dotenv()
    synthetic_analysis = {
        "match_level": "semantic",
        "evidence": {
            "observation_count": 3,
            "median_unit_price": 900000,
            "currency": "NGN",
        },
        "quote_comparison": {
            "quoted_unit_price": 850000,
            "position": "below_observed_range",
        },
        "recommendation": {
            "confidence": "low",
            "recommended_action": "gather_more_evidence",
            "reason_codes": ["non_exact_product_match"],
        },
    }
    text = build_explanation_chain().invoke(
        {"analysis_json": json.dumps(synthetic_analysis)}
    )
    generated = str(text).strip()
    print("langchain_huggingface=connected")
    print(f"generated_text_nonempty={bool(generated)}")
    print(f"generated_length={len(generated)}")
    if not generated:
        raise RuntimeError("The explanation model returned empty visible text")


if __name__ == "__main__":
    main()
