from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.api.deps import get_current_user, require_buyer
from app.db.session import get_db
from app.models.user import User
from app.schemas.rfq import RFQCreate, RFQDetailResponse, RFQListItem
from app.services.rfq_service import RFQService
from app.websocket.manager import ws_manager

router = APIRouter(prefix="/rfqs", tags=["RFQs & British Auctions"])


@router.post("", response_model=RFQDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_rfq(
    rfq_in: RFQCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_buyer)
):
    service = RFQService(db)
    existing = service.get_rfq_by_reference(rfq_in.reference_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"RFQ Reference ID '{rfq_in.reference_id}' already exists."
        )

    rfq = service.create_rfq(rfq_in, creator_id=current_user.id)
    detail = service.get_rfq_detail(rfq.id)

    # Broadcast new auction event to dashboard/listings
    await ws_manager.broadcast_to_general({
        "event_type": "AUCTION_CREATED",
        "rfq_id": rfq.id,
        "reference_id": rfq.reference_id,
        "title": rfq.title,
        "status": rfq.status
    })

    return detail


@router.get("", response_model=List[RFQListItem])
def list_rfqs(
    status: Optional[str] = Query(None, description="Filter by status: ACTIVE, CLOSED, FORCE_CLOSED, or ALL"),
    search: Optional[str] = Query(None, description="Search by title, reference ID, origin, destination"),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user)
):
    service = RFQService(db)
    return service.list_rfqs(status=status, search=search)


@router.get("/{rfq_id}", response_model=RFQDetailResponse)
def get_rfq_details(
    rfq_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user)
):
    service = RFQService(db)
    detail = service.get_rfq_detail(rfq_id)
    if not detail:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="RFQ not found")
    return detail
