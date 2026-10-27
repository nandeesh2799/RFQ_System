from datetime import date, datetime, timezone
from typing import List
from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.constants import AuctionStatus, ExtensionTriggerMode
from app.db.base import Base


class RFQ(Base):
    __tablename__ = "rfqs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    reference_id: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    origin: Mapped[str] = mapped_column(String(255), nullable=False)
    destination: Mapped[str] = mapped_column(String(255), nullable=False)
    cargo_details: Mapped[str] = mapped_column(String(255), nullable=False)
    pickup_date: Mapped[date] = mapped_column(Date, nullable=False)

    british_auction_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    bid_start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    bid_close_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    current_close_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    forced_close_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)

    trigger_window_minutes: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    extension_duration_minutes: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    extension_trigger_mode: Mapped[str] = mapped_column(
        String(50),
        default=ExtensionTriggerMode.BID_RECEIVED.value,
        nullable=False
    )

    status: Mapped[str] = mapped_column(
        String(50),
        default=AuctionStatus.ACTIVE.value,
        index=True,
        nullable=False
    )

    current_lowest_bid: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    current_l1_supplier_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    creator = relationship("User", back_populates="rfqs", foreign_keys=[created_by_user_id])
    l1_supplier = relationship("User", foreign_keys=[current_l1_supplier_id])
    bids: Mapped[List["Bid"]] = relationship("Bid", back_populates="rfq", cascade="all, delete-orphan")
    extensions: Mapped[List["AuctionExtension"]] = relationship("AuctionExtension", back_populates="rfq", cascade="all, delete-orphan")
    activities: Mapped[List["AuctionActivityLog"]] = relationship("AuctionActivityLog", back_populates="rfq", cascade="all, delete-orphan")
