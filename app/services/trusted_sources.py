import re
from dataclasses import dataclass


@dataclass(frozen=True)
class TrustedSource:
    name: str
    url: str
    description: str


@dataclass(frozen=True)
class SourceTopic:
    pattern: re.Pattern[str]
    sources: tuple[TrustedSource, ...]


SOURCE_TOPICS = (
    SourceTopic(
        pattern=re.compile(r"\b(weather|forecast|rain|temperature|climate)\b", re.I),
        sources=(
            TrustedSource(
                "Nigerian Meteorological Agency (NiMet)",
                "https://nimet.gov.ng/",
                "Official Nigerian forecasts and weather advisories",
            ),
            TrustedSource(
                "World Meteorological Organization",
                "https://worldweather.wmo.int/",
                "Official forecasts supplied by national weather services",
            ),
        ),
    ),
    SourceTopic(
        pattern=re.compile(
            r"\b(latest news|breaking news|trending news|news headlines?|viral content|viral stories|what(?:'s| is) trending)\b",
            re.I,
        ),
        sources=(
            TrustedSource(
                "Google Trends — Trending Now",
                "https://trends.google.com/trending",
                "Recently surging Google searches with regional and time filters",
            ),
            TrustedSource(
                "Google News",
                "https://news.google.com/",
                "Current reporting grouped across multiple publishers",
            ),
        ),
    ),
    SourceTopic(
        pattern=re.compile(r"\b(exchange rate|forex|fx rate|currency rate|naira rate)\b", re.I),
        sources=(
            TrustedSource(
                "Central Bank of Nigeria exchange rates",
                "https://www.cbn.gov.ng/rates/ExchRateByCurrency.html",
                "Official Nigerian foreign-exchange market rates",
            ),
        ),
    ),
    SourceTopic(
        pattern=re.compile(r"\b(procurement law|procurement regulation|public procurement|bidding rules?)\b", re.I),
        sources=(
            TrustedSource(
                "Bureau of Public Procurement",
                "https://bpp.gov.ng/downloads/",
                "Nigerian procurement laws, regulations, manuals, and guidelines",
            ),
        ),
    ),
    SourceTopic(
        pattern=re.compile(r"\b(dell support|dell driver|dell warranty)\b", re.I),
        sources=(
            TrustedSource(
                "Dell Support",
                "https://www.dell.com/support/home/",
                "Official drivers, warranty checks, and product support",
            ),
        ),
    ),
)


def trusted_sources_for(message: str) -> tuple[TrustedSource, ...]:
    for topic in SOURCE_TOPICS:
        if topic.pattern.search(message):
            return topic.sources
    return ()


def append_trusted_sources(reply: str, message: str) -> str:
    sources = trusted_sources_for(message)
    if not sources:
        return reply
    # For these outside-domain topics, discard model-generated URLs before adding
    # the reviewed directory entries below.
    reply = re.sub(r"\[([^\]]+)\]\(https?://[^)]+\)", r"\1", reply)
    reply = re.sub(r"https?://\S+", "", reply)
    links = "\n".join(
        f"- [{source.name}]({source.url}) — {source.description}."
        for source in sources
    )
    return f"{reply.rstrip()}\n\n**Trusted places to check:**\n{links}"
