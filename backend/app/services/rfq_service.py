from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session
from app.core.clock import Clock, SystemClock
from app.core.constants import ActivityType, AuctionStatus
from app.models.activity import AuctionActivityLog
from app.models.bid import Bid
from app.models.rfq import RFQ
from app.models.user import User
from app.schemas.bid import SupplierRankingItem
from app.schemas.rfq import DashboardStats, RFQCreate, RFQDetailResponse, RFQListItem
from app.services.auction_engine import AuctionEngine, SupplierBidSummary


class RFQService:
    def __init__(self, db: Session, clock: Clock = SystemClock()):
        self.db = db
        self.clock = clock

    def create_rfq(self, data: RFQCreate, creator_id: int) -> RFQ:
        now = self.clock.now()

        # Initial status evaluation
        status = AuctionEngine.determine_status(
            bid_start_time=data.bid_start_time,
            current_close_time=data.bid_close_time,
            forced_close_time=data.forced_close_time,
            current_time=now,
            current_status=AuctionStatus.ACTIVE.value
        ).value

        rfq = RFQ(
            title=data.title,
            reference_id=data.reference_id,
            description=data.description,
            origin=data.origin,
            destination=data.destination,
            cargo_details=data.cargo_details,
            pickup_date=data.pickup_date,
            british_auction_enabled=data.british_auction_enabled,
            bid_start_time=data.bid_start_time,
            bid_close_time=data.bid_close_time,
            current_close_time=data.bid_close_time,  # starts equal to initial close time
            forced_close_time=data.forced_close_time,
            trigger_window_minutes=data.trigger_window_minutes,
            extension_duration_minutes=data.extension_duration_minutes,
            extension_trigger_mode=data.extension_trigger_mode.value,
            status=status,
            created_by_user_id=creator_id,
        )
        self.db.add(rfq)
        self.db.flush()

        # Log auction created activity
        log = AuctionActivityLog(
            rfq_id=rfq.id,
            actor_id=creator_id,
            activity_type=ActivityType.AUCTION_CREATED.value,
            headline=f"RFQ {rfq.reference_id} created with British Auction enabled",
            details=(
                f"Mode: {rfq.extension_trigger_mode}, Trigger Window: {rfq.trigger_window_minutes}m, "
                f"Extension: {rfq.extension_duration_minutes}m, Forced Close: {rfq.forced_close_time.isoformat()}"
            ),
        )
        self.db.add(log)
        self.db.commit()
        self.db.refresh(rfq)
        return rfq

    def get_rfq_by_id(self, rfq_id: int) -> Optional[RFQ]:
        return self.db.query(RFQ).filter(RFQ.id == rfq_id).first()

    def get_rfq_by_reference(self, reference_id: str) -> Optional[RFQ]:
        return self.db.query(RFQ).filter(RFQ.reference_id == reference_id).first()

    def update_rfq_status_if_needed(self, rfq: RFQ) -> str:
        now = self.clock.now()
        new_status = AuctionEngine.determine_status(
            bid_start_time=rfq.bid_start_time,
            current_close_time=rfq.current_close_time,
            forced_close_time=rfq.forced_close_time,
            current_time=now,
            current_status=rfq.status
        ).value

        if new_status != rfq.status:
            old_status = rfq.status
            rfq.status = new_status
            self.db.add(rfq)

            activity_type = (
                ActivityType.FORCED_CLOSE_TRIGGERED.value
                if new_status == AuctionStatus.FORCE_CLOSED.value
                else ActivityType.STATUS_CHANGED.value
            )
            log = AuctionActivityLog(
                rfq_id=rfq.id,
                activity_type=activity_type,
                headline=f"Auction status transitioned to {new_status}",
                details=f"Status changed from {old_status} to {new_status} at {now.isoformat()}.",
            )
            self.db.add(log)
            self.db.commit()
            self.db.refresh(rfq)

        return rfq.status

    def list_rfqs(self, status: Optional[str] = None, search: Optional[str] = None) -> List[RFQListItem]:
        query = self.db.query(RFQ)
        if status and status != "ALL":
            query = query.filter(RFQ.status == status)
        if search:
            pattern = f"%{search}%"
            query = query.filter(
                (RFQ.title.ilike(pattern)) |
                (RFQ.reference_id.ilike(pattern)) |
                (RFQ.origin.ilike(pattern)) |
                (RFQ.destination.ilike(pattern))
            )

        rfqs = query.order_by(desc(RFQ.created_at)).all()
        result: List[RFQListItem] = []

        for r in rfqs:
            self.update_rfq_status_if_needed(r)
            bids_count = self.db.query(func.count(Bid.id)).filter(Bid.rfq_id == r.id).scalar() or 0
            l1_user = self.db.query(User).filter(User.id == r.current_l1_supplier_id).first() if r.current_l1_supplier_id else None

            result.append(RFQListItem(
                id=r.id,
                title=r.title,
                reference_id=r.reference_id,
                origin=r.origin,
                destination=r.destination,
                pickup_date=r.pickup_date,
                british_auction_enabled=r.british_auction_enabled,
                bid_start_time=r.bid_start_time,
                bid_close_time=r.bid_close_time,
                current_close_time=r.current_close_time,
                forced_close_time=r.forced_close_time,
                trigger_window_minutes=r.trigger_window_minutes,
                extension_duration_minutes=r.extension_duration_minutes,
                extension_trigger_mode=r.extension_trigger_mode,
                status=r.status,
                current_lowest_bid=r.current_lowest_bid,
                total_bids_count=bids_count,
                l1_supplier_name=l1_user.company_name if l1_user else None,
                created_at=r.created_at
            ))
        return result

    def get_rfq_detail(self, rfq_id: int) -> Optional[RFQDetailResponse]:
        rfq = self.get_rfq_by_id(rfq_id)
        if not rfq:
            return None

        self.update_rfq_status_if_needed(rfq)
        now = self.clock.now()

        # Calculate time remaining
        remaining_seconds = max(0, int((rfq.current_close_time - now).total_seconds()))
        in_window = AuctionEngine.is_in_trigger_window(
            current_close_time=rfq.current_close_time,
            trigger_window_minutes=rfq.trigger_window_minutes,
            submission_time=now
        )
        has_reached_forced = (rfq.current_close_time >= rfq.forced_close_time) or (now >= rfq.forced_close_time)

        # Get all bids
        bids = self.db.query(Bid).filter(Bid.rfq_id == rfq.id).order_by(desc(Bid.submitted_at)).all()

        # Convert to summaries for pure ranking calculation
        summaries = [
            SupplierBidSummary(
                supplier_id=b.supplier_id,
                supplier_name=b.supplier.company_name if b.supplier else f"Supplier #{b.supplier_id}",
                total_quote_amount=b.total_quote_amount,
                submitted_at=b.submitted_at,
                carrier_name=b.carrier_name,
                bid_id=b.id
            )
            for b in bids if b.is_valid
        ]

        ranked_engine_results = AuctionEngine.calculate_rankings(summaries)
        rank_map = {r.bid_id: r.rank for r in ranked_engine_results}

        # Build supplier ranking items
        bid_map = {b.id: b for b in bids}
        ranking_items: List[SupplierRankingItem] = []
        for r in ranked_engine_results:
            original_bid = bid_map.get(r.bid_id)
            if original_bid:
                ranking_items.append(SupplierRankingItem(
                    rank=r.rank,
                    supplier_id=r.supplier_id,
                    supplier_name=r.supplier_name,
                    company_name=original_bid.supplier.company_name if original_bid.supplier else r.supplier_name,
                    carrier_name=original_bid.carrier_name,
                    total_quote_amount=original_bid.total_quote_amount,
                    freight_charges=original_bid.freight_charges,
                    origin_charges=original_bid.origin_charges,
                    destination_charges=original_bid.destination_charges,
                    transit_time_days=original_bid.transit_time_days,
                    quote_validity_date=original_bid.quote_validity_date,
                    submitted_at=original_bid.submitted_at,
                    bid_id=original_bid.id
                ))

        extensions = sorted(rfq.extensions, key=lambda x: x.extended_at, reverse=True)
        activities = sorted(rfq.activities, key=lambda x: x.created_at, reverse=True)

        return RFQDetailResponse(
            id=rfq.id,
            title=rfq.title,
            reference_id=rfq.reference_id,
            description=rfq.description,
            origin=rfq.origin,
            destination=rfq.destination,
            cargo_details=rfq.cargo_details,
            pickup_date=rfq.pickup_date,
            british_auction_enabled=rfq.british_auction_enabled,
            bid_start_time=rfq.bid_start_time,
            bid_close_time=rfq.bid_close_time,
            current_close_time=rfq.current_close_time,
            forced_close_time=rfq.forced_close_time,
            trigger_window_minutes=rfq.trigger_window_minutes,
            extension_duration_minutes=rfq.extension_duration_minutes,
            extension_trigger_mode=rfq.extension_trigger_mode,
            status=rfq.status,
            current_lowest_bid=rfq.current_lowest_bid,
            time_remaining_seconds=remaining_seconds,
            is_in_trigger_window=in_window,
            has_reached_forced_close=has_reached_forced,
            creator=rfq.creator,
            rankings=ranking_items,
            bids=bids,
            extensions=extensions,
            activities=activities,
            created_at=rfq.created_at,
            updated_at=rfq.updated_at,
        )

    def get_dashboard_stats(self) -> DashboardStats:
        total = self.db.query(func.count(RFQ.id)).scalar() or 0
        active = self.db.query(func.count(RFQ.id)).filter(RFQ.status == AuctionStatus.ACTIVE.value).scalar() or 0
        closed = self.db.query(func.count(RFQ.id)).filter(RFQ.status == AuctionStatus.CLOSED.value).scalar() or 0
        force_closed = self.db.query(func.count(RFQ.id)).filter(RFQ.status == AuctionStatus.FORCE_CLOSED.value).scalar() or 0

        # Recent activities
        recent_acts = self.db.query(AuctionActivityLog).order_by(desc(AuctionActivityLog.created_at)).limit(10).all()

        # Active auctions with lowest bids
        active_rfqs = self.list_rfqs(status=AuctionStatus.ACTIVE.value)

        # Upcoming deadlines
        upcoming = sorted(active_rfqs, key=lambda x: x.current_close_time)[:5]

        return DashboardStats(
            total_rfqs=total,
            active_auctions=active,
            closed_auctions=closed,
            force_closed_auctions=force_closed,
            recent_activities=recent_acts,
            active_lowest_bids=active_rfqs[:5],
            upcoming_deadlines=upcoming
        )
