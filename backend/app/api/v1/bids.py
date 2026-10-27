from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.api.deps import get_current_user, require_supplier
from app.db.session import get_db
from app.models.bid import Bid
from app.models.user import User
from app.schemas.bid import BidCreate, BidResponse, SupplierRankingItem
from app.services.bid_service import BidService
from app.services.rfq_service import RFQService
from app.websocket.manager import ws_manager

router = APIRouter(prefix="/rfqs/{rfq_id}/bids", tags=["Quotes & Bids"])


@router.post("", response_model=BidResponse, status_code=status.HTTP_201_CREATED)
async def submit_bid(
    rfq_id: int,
    bid_in: BidCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_supplier)
):
    bid_service = BidService(db)
    bid, extension_res, rankings = bid_service.submit_bid(
        rfq_id=rfq_id,
        bid_in=bid_in,
        supplier_id=current_user.id
    )

    rfq_service = RFQService(db)
    detail = rfq_service.get_rfq_detail(rfq_id)

    # Broadcast real-time update to this auction room
    event_payload = {
        "event_type": "BID_SUBMITTED",
        "rfq_id": rfq_id,
        "bid_id": bid.id,
        "supplier_id": current_user.id,
        "supplier_name": current_user.company_name,
        "carrier_name": bid.carrier_name,
        "total_quote_amount": float(bid.total_quote_amount),
        "rank": bid.rank_at_submission,
        "extended": extension_res.should_extend,
        "new_close_time": extension_res.new_close_time.isoformat(),
        "extension_minutes": extension_res.extension_minutes_applied,
        "extension_reason": extension_res.reason,
        "rankings": [
            {
                "rank": r.rank,
                "supplier_name": r.supplier_name,
                "total_quote_amount": float(r.total_quote_amount),
                "carrier_name": r.carrier_name
            }
            for r in rankings
        ]
    }
    await ws_manager.broadcast_to_auction(rfq_id, event_payload)

    # Broadcast to general listings/dashboard
    await ws_manager.broadcast_to_general({
        "event_type": "AUCTION_ACTIVITY",
        "rfq_id": rfq_id,
        "lowest_bid": float(detail.current_lowest_bid) if detail.current_lowest_bid else None,
        "extended": extension_res.should_extend,
        "new_close_time": extension_res.new_close_time.isoformat(),
    })

    return bid


@router.get("", response_model=List[BidResponse])
def get_rfq_bids(
    rfq_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user)
):
    bids = db.query(Bid).filter(Bid.rfq_id == rfq_id).order_by(Bid.submitted_at.desc()).all()
    return bids
