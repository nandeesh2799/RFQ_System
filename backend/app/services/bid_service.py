from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.core.clock import Clock, SystemClock
from app.core.constants import ActivityType, AuctionStatus
from app.models.activity import AuctionActivityLog
from app.models.bid import Bid
from app.models.extension import AuctionExtension
from app.models.rfq import RFQ
from app.models.user import User
from app.schemas.bid import BidCreate
from app.services.auction_engine import AuctionEngine, ExtensionEvaluationResult, RankedSupplier, SupplierBidSummary


class BidService:
    def __init__(self, db: Session, clock: Clock = SystemClock()):
        self.db = db
        self.clock = clock

    def submit_bid(
        self,
        rfq_id: int,
        bid_in: BidCreate,
        supplier_id: int
    ) -> Tuple[Bid, ExtensionEvaluationResult, List[RankedSupplier]]:
        """
        Submits a supplier quote with ACID transaction, row-level locking,
        strict price descending enforcement, ranking evaluation, and extension triggers.
        """
        now = self.clock.now()

        # Step 1: Row-level lock on the RFQ record to prevent race conditions
        rfq = (
            self.db.query(RFQ)
            .filter(RFQ.id == rfq_id)
            .with_for_update()
            .first()
        )
        if not rfq:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="RFQ not found")

        # Step 2: Validate supplier
        supplier = self.db.query(User).filter(User.id == supplier_id).first()
        if not supplier:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier user not found")

        # Step 3: Check auction eligibility & status
        current_status = AuctionEngine.determine_status(
            bid_start_time=rfq.bid_start_time,
            current_close_time=rfq.current_close_time,
            forced_close_time=rfq.forced_close_time,
            current_time=now,
            current_status=rfq.status
        )
        if current_status != AuctionStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot submit bid: Auction is {current_status.value}."
            )
        if rfq.status != current_status.value:
            rfq.status = current_status.value

        eligible, reason = AuctionEngine.is_bid_eligible(
            bid_start_time=rfq.bid_start_time,
            current_close_time=rfq.current_close_time,
            forced_close_time=rfq.forced_close_time,
            submission_time=now
        )
        if not eligible:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=reason)

        # Step 4: Calculate total quote amount server-side
        try:
            total_amount = AuctionEngine.calculate_total_quote(
                freight_charges=bid_in.freight_charges,
                origin_charges=bid_in.origin_charges,
                destination_charges=bid_in.destination_charges
            )
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

        # Step 5: Check descending price competition rule:
        # A supplier cannot submit a bid higher than their own previous best bid
        existing_supplier_bids = (
            self.db.query(Bid)
            .filter(Bid.rfq_id == rfq.id, Bid.supplier_id == supplier_id, Bid.is_valid == True)
            .all()
        )
        if existing_supplier_bids:
            min_existing = min(b.total_quote_amount for b in existing_supplier_bids)
            if total_amount > min_existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"Descending price rule: Your new quote (${total_amount:,.2f}) must be lower "
                        f"than or equal to your current best quote (${min_existing:,.2f})."
                    )
                )

        # Step 6: Collect all valid bids before this submission for ranking calculation
        all_prior_bids = (
            self.db.query(Bid)
            .filter(Bid.rfq_id == rfq.id, Bid.is_valid == True)
            .order_by(Bid.submitted_at.asc())
            .all()
        )

        prior_summaries = [
            SupplierBidSummary(
                supplier_id=b.supplier_id,
                supplier_name=b.supplier.company_name if b.supplier else f"Supplier #{b.supplier_id}",
                total_quote_amount=b.total_quote_amount,
                submitted_at=b.submitted_at,
                carrier_name=b.carrier_name,
                bid_id=b.id
            )
            for b in all_prior_bids
        ]

        # Step 7: Create and persist new Bid
        new_bid = Bid(
            rfq_id=rfq.id,
            supplier_id=supplier_id,
            carrier_name=bid_in.carrier_name,
            freight_charges=bid_in.freight_charges,
            origin_charges=bid_in.origin_charges,
            destination_charges=bid_in.destination_charges,
            total_quote_amount=total_amount,
            transit_time_days=bid_in.transit_time_days,
            quote_validity_date=bid_in.quote_validity_date,
            submitted_at=now,
            is_valid=True,
            notes=bid_in.notes
        )
        self.db.add(new_bid)
        self.db.flush()

        new_summary = SupplierBidSummary(
            supplier_id=supplier.id,
            supplier_name=supplier.company_name,
            total_quote_amount=total_amount,
            submitted_at=now,
            carrier_name=new_bid.carrier_name,
            bid_id=new_bid.id
        )

        # Step 8: Evaluate rankings after and stamp rank_at_submission
        rankings_after = AuctionEngine.calculate_rankings(prior_summaries + [new_summary])
        current_rank = next((r.rank for r in rankings_after if r.supplier_id == supplier.id), None)
        new_bid.rank_at_submission = current_rank
        self.db.add(new_bid)

        # Step 9: Evaluate British Auction extension
        extension_res = AuctionEngine.evaluate_extension(
            trigger_mode=rfq.extension_trigger_mode,
            trigger_window_minutes=rfq.trigger_window_minutes,
            extension_duration_minutes=rfq.extension_duration_minutes,
            current_close_time=rfq.current_close_time,
            forced_close_time=rfq.forced_close_time,
            submission_time=now,
            bids_before=prior_summaries,
            new_bid=new_summary,
            british_auction_enabled=rfq.british_auction_enabled,
        )

        # Step 10: Apply extension if qualified
        if extension_res.should_extend:
            previous_close = rfq.current_close_time
            rfq.current_close_time = extension_res.new_close_time

            extension_record = AuctionExtension(
                rfq_id=rfq.id,
                bid_id=new_bid.id,
                extended_at=now,
                previous_close_time=previous_close,
                new_close_time=extension_res.new_close_time,
                extension_minutes=extension_res.extension_minutes_applied,
                trigger_mode=rfq.extension_trigger_mode,
                trigger_reason=extension_res.reason
            )
            self.db.add(extension_record)

            # Activity log for extension
            ext_log = AuctionActivityLog(
                rfq_id=rfq.id,
                bid_id=new_bid.id,
                actor_id=supplier_id,
                activity_type=ActivityType.EXTENSION_TRIGGERED.value,
                headline=f"Auction extended by {extension_res.extension_minutes_applied} minutes",
                details=extension_res.reason,
                extra_metadata={
                    "previous_close_time": previous_close.isoformat(),
                    "new_close_time": extension_res.new_close_time.isoformat(),
                    "extension_minutes": extension_res.extension_minutes_applied,
                    "forced_close_time": rfq.forced_close_time.isoformat(),
                }
            )
            self.db.add(ext_log)

        # Step 11: Update RFQ lowest bid and L1 supplier
        if rankings_after:
            l1_bid = rankings_after[0]
            rfq.current_lowest_bid = l1_bid.total_quote_amount
            rfq.current_l1_supplier_id = l1_bid.supplier_id
        self.db.add(rfq)

        # Step 12: Activity log for bid submission
        rank_str = f"Rank L{current_rank}" if current_rank else "Unranked"
        bid_log = AuctionActivityLog(
            rfq_id=rfq.id,
            bid_id=new_bid.id,
            actor_id=supplier_id,
            activity_type=ActivityType.BID_SUBMITTED.value,
            headline=f"New bid submitted by {supplier.company_name}: ${total_amount:,.2f} ({rank_str})",
            details=(
                f"Carrier: {new_bid.carrier_name}, Freight: ${new_bid.freight_charges:,.2f}, "
                f"Origin: ${new_bid.origin_charges:,.2f}, Dest: ${new_bid.destination_charges:,.2f}, "
                f"Transit: {new_bid.transit_time_days} days."
            ),
            extra_metadata={
                "total_quote_amount": float(total_amount),
                "rank": current_rank,
                "in_trigger_window": extension_res.is_in_window
            }
        )
        self.db.add(bid_log)

        # Commit ACID transaction
        self.db.commit()
        self.db.refresh(new_bid)
        self.db.refresh(rfq)

        return new_bid, extension_res, rankings_after
