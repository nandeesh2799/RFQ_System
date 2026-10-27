from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, Field, field_validator
from app.schemas.user import UserResponse


class BidCreate(BaseModel):
    carrier_name: str = Field(..., min_length=2, max_length=255, description="Operating carrier name")
    freight_charges: Decimal = Field(..., ge=0, description="Base freight charges")
    origin_charges: Decimal = Field(..., ge=0, description="Origin terminal and handling charges")
    destination_charges: Decimal = Field(..., ge=0, description="Destination terminal and handling charges")
    transit_time_days: int = Field(..., ge=1, le=180, description="Estimated transit time in days")
    quote_validity_date: date = Field(..., description="Validity expiration date of the quotation")
    notes: str | None = None

    @field_validator("carrier_name")
    @classmethod
    def validate_carrier_name(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Carrier name cannot be blank")
        return trimmed


class BidResponse(BaseModel):
    id: int
    rfq_id: int
    supplier_id: int
    carrier_name: str
    freight_charges: Decimal
    origin_charges: Decimal
    destination_charges: Decimal
    total_quote_amount: Decimal
    transit_time_days: int
    quote_validity_date: date
    submitted_at: datetime
    is_valid: bool
    rank_at_submission: int | None
    notes: str | None
    supplier: UserResponse | None = None

    class Config:
        from_attributes = True


class SupplierRankingItem(BaseModel):
    rank: int
    supplier_id: int
    supplier_name: str
    company_name: str
    carrier_name: str
    total_quote_amount: Decimal
    freight_charges: Decimal
    origin_charges: Decimal
    destination_charges: Decimal
    transit_time_days: int
    quote_validity_date: date
    submitted_at: datetime
    bid_id: int
