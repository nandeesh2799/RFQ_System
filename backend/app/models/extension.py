from datetime import datetime, timezone
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class AuctionExtension(Base):
    __tablename__ = "auction_extensions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    rfq_id: Mapped[int] = mapped_column(ForeignKey("rfqs.id", ondelete="CASCADE"), nullable=False, index=True)
    bid_id: Mapped[int | None] = mapped_column(ForeignKey("bids.id", ondelete="SET NULL"), nullable=True, index=True)

    extended_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )
    previous_close_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    new_close_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    extension_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    trigger_mode: Mapped[str] = mapped_column(String(50), nullable=False)
    trigger_reason: Mapped[str] = mapped_column(Text, nullable=False)

    rfq = relationship("RFQ", back_populates="extensions")
    bid = relationship("Bid")
