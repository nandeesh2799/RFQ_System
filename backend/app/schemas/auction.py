from datetime import datetime
from typing import Any, Dict
from pydantic import BaseModel
from app.schemas.user import UserResponse


class ExtensionRecordResponse(BaseModel):
    id: int
    rfq_id: int
    bid_id: int | None
    extended_at: datetime
    previous_close_time: datetime
    new_close_time: datetime
    extension_minutes: int
    trigger_mode: str
    trigger_reason: str

    class Config:
        from_attributes = True


class ActivityLogResponse(BaseModel):
    id: int
    rfq_id: int
    bid_id: int | None
    actor_id: int | None
    activity_type: str
    headline: str
    details: str | None
    extra_metadata: Dict[str, Any] | None
    created_at: datetime
    actor: UserResponse | None = None

    class Config:
        from_attributes = True
