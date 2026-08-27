import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class MarketPriceObservation(Base):
    """A dated supplier price observed for a specific laptop configuration."""

    __tablename__ = "market_price_observations"
    __table_args__ = (
        CheckConstraint("ram_gb > 0", name="ck_market_observation_ram_positive"),
        CheckConstraint(
            "storage_capacity_gb > 0",
            name="ck_market_observation_storage_positive",
        ),
        CheckConstraint("quantity > 0", name="ck_market_observation_quantity_positive"),
        CheckConstraint("unit_price > 0", name="ck_market_observation_price_positive"),
        CheckConstraint(
            "source_reliability >= 0 AND source_reliability <= 1",
            name="ck_market_observation_reliability_range",
        ),
        CheckConstraint(
            "condition IN ('new', 'used', 'refurbished')",
            name="ck_market_observation_condition",
        ),
        CheckConstraint(
            "storage_type IN ('ssd', 'hdd', 'emmc', 'unknown')",
            name="ck_market_observation_storage_type",
        ),
        UniqueConstraint(
            "source_name",
            "source_external_id",
            "observation_date",
            name="uq_market_observation_source_daily",
        ),
        Index(
            "ix_market_observation_comparable_lookup",
            "manufacturer",
            "model_number",
            "ram_gb",
            "storage_capacity_gb",
            "condition",
            "observation_date",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Product identity
    product_name: Mapped[str] = mapped_column(String(200), nullable=False)
    manufacturer: Mapped[str] = mapped_column(String(100), nullable=False)
    product_line: Mapped[str | None] = mapped_column(String(100))
    model_number: Mapped[str] = mapped_column(String(100), nullable=False)

    # Comparable specifications
    cpu: Mapped[str] = mapped_column(String(150), nullable=False)
    ram_gb: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_capacity_gb: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_type: Mapped[str] = mapped_column(String(20), nullable=False)
    condition: Mapped[str] = mapped_column(String(20), nullable=False)

    # Supplier and market location
    supplier_name: Mapped[str] = mapped_column(String(200), nullable=False)
    location_city: Mapped[str | None] = mapped_column(String(100))
    location_country: Mapped[str] = mapped_column(String(100), nullable=False)

    # Observed offer
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)

    # Evidence provenance
    source_name: Mapped[str] = mapped_column(String(200), nullable=False)
    source_url: Mapped[str | None] = mapped_column(Text)
    source_external_id: Mapped[str | None] = mapped_column(String(100))
    observation_date: Mapped[date] = mapped_column(Date, nullable=False)
    source_reliability: Mapped[Decimal] = mapped_column(Numeric(3, 2), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
