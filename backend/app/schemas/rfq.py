from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, Field, model_validator
from app.core.constants import AuctionStatus, ExtensionTriggerMode
from app.schemas.auction import ActivityLogResponse, ExtensionRecordResponse
from app.schemas.bid import BidResponse, SupplierRankingItem
from app.schemas.user import UserResponse


class RFQCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=255, description="RFQ Title or Description")
    reference_id: str = Field(..., min_length=3, max_length=100, description="Unique reference ID, e.g. RFQ-2026-001")
    description: Optional[str] = None
    origin: str = Field(..., min_length=2, max_length=255, description="Origin port or warehouse")
    destination: str = Field(..., min_length=2, max_length=255, description="Destination port or warehouse")
    cargo_details: str = Field(..., min_length=2, max_length=255, description="Cargo volume, weight, container type")
    pickup_date: date = Field(..., description="Service or pickup commencement date")

    british_auction_enabled: bool = Field(True, description="Enable British Auction dynamic extension rules")

    bid_start_time: datetime = Field(..., description="Auction bidding start time (UTC)")
    bid_close_time: datetime = Field(..., description="Initial scheduled close time (UTC)")
    forced_close_time: datetime = Field(..., description="Forced close deadline (UTC)")

    trigger_window_minutes: int = Field(10, ge=1, le=1440, description="Trigger window X in minutes")
    extension_duration_minutes: int = Field(5, ge=1, le=1440, description="Extension duration Y in minutes")
    extension_trigger_mode: ExtensionTriggerMode = Field(
        ExtensionTriggerMode.BID_RECEIVED,
        description="Trigger mode: BID_RECEIVED, ANY_RANK_CHANGE, or L1_RANK_CHANGE"
    )

    @model_validator(mode="after")
    def validate_times(self) -> "RFQCreate":
        if self.bid_start_time >= self.bid_close_time:
            raise ValueError("Bid start time must be earlier than the initial bid close time.")
        if self.forced_close_time <= self.bid_close_time:
            raise ValueError("Forced bid close time must be strictly later than the initial bid close time.")
        return self


class RFQListItem(BaseModel):
    id: int
    title: str
    reference_id: str
    origin: str
    destination: str
    pickup_date: date
    british_auction_enabled: bool
    bid_start_time: datetime
    bid_close_time: datetime
    current_close_time: datetime
    forced_close_time: datetime
    trigger_window_minutes: int
    extension_duration_minutes: int
    extension_trigger_mode: str
    status: str
    current_lowest_bid: Optional[Decimal] = None
    total_bids_count: int = 0
    l1_supplier_name: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class RFQDetailResponse(BaseModel):
    id: int
    title: str
    reference_id: str
    description: Optional[str]
    origin: str
    destination: str
    cargo_details: str
    pickup_date: date
    british_auction_enabled: bool
    bid_start_time: datetime
    bid_close_time: datetime
    current_close_time: datetime
    forced_close_time: datetime
    trigger_window_minutes: int
    extension_duration_minutes: int
    extension_trigger_mode: str
    status: str
    current_lowest_bid: Optional[Decimal] = None
    time_remaining_seconds: int = 0
    is_in_trigger_window: bool = False
    has_reached_forced_close: bool = False
    creator: Optional[UserResponse] = None
    rankings: List[SupplierRankingItem] = []
    bids: List[BidResponse] = []
    extensions: List[ExtensionRecordResponse] = []
    activities: List[ActivityLogResponse] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DashboardStats(BaseModel):
    total_rfqs: int
    active_auctions: int
    closed_auctions: int
    force_closed_auctions: int
    recent_activities: List[ActivityLogResponse]
    active_lowest_bids: List[RFQListItem]
    upcoming_deadlines: List[RFQListItem]
