from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from app.core.constants import AuctionStatus, ExtensionTriggerMode


@dataclass(frozen=True)
class SupplierBidSummary:
    supplier_id: int
    supplier_name: str
    total_quote_amount: Decimal
    submitted_at: datetime
    carrier_name: str
    bid_id: int


@dataclass(frozen=True)
class RankedSupplier:
    rank: int  # 1 for L1, 2 for L2, etc.
    supplier_id: int
    supplier_name: str
    total_quote_amount: Decimal
    submitted_at: datetime
    carrier_name: str
    bid_id: int


@dataclass(frozen=True)
class ExtensionEvaluationResult:
    should_extend: bool
    trigger_mode: str
    is_in_window: bool
    previous_close_time: datetime
    new_close_time: datetime
    extension_minutes_applied: int
    reason: str
    l1_changed: bool
    rankings_changed: bool
    rank_before: Optional[int]
    rank_after: Optional[int]


class AuctionEngine:
    """Pure domain logic for British Auction calculations, validations, rankings, and extensions."""

    @staticmethod
    def calculate_total_quote(
        freight_charges: Decimal,
        origin_charges: Decimal,
        destination_charges: Decimal
    ) -> Decimal:
        """Calculates total quote amount = freight + origin + destination charges."""
        if freight_charges < 0 or origin_charges < 0 or destination_charges < 0:
            raise ValueError("Quote charges cannot be negative")
        return (freight_charges + origin_charges + destination_charges).quantize(Decimal("0.01"))

    @staticmethod
    def is_bid_eligible(
        bid_start_time: datetime,
        current_close_time: datetime,
        forced_close_time: datetime,
        submission_time: datetime
    ) -> Tuple[bool, Optional[str]]:
        """
        Validates if bid is submitted within the eligible auction window:
        Rule: bid_start_time <= submission_time < current_close_time AND submission_time < forced_close_time
        """
        if submission_time < bid_start_time:
            return False, f"Bidding has not started yet. Starts at {bid_start_time.isoformat()}."
        if submission_time >= forced_close_time:
            return False, f"Auction has reached its forced close deadline ({forced_close_time.isoformat()}). No further bids accepted."
        if submission_time >= current_close_time:
            return False, f"Auction has closed at {current_close_time.isoformat()}."
        return True, None

    @staticmethod
    def is_in_trigger_window(
        current_close_time: datetime,
        trigger_window_minutes: int,
        submission_time: datetime
    ) -> bool:
        """
        Checks if the bid falls inside [current_close_time - trigger_window_minutes, current_close_time).
        Notice: Window is calculated relative to dynamic current_close_time.
        """
        window_start = current_close_time - timedelta(minutes=trigger_window_minutes)
        return window_start <= submission_time < current_close_time

    @staticmethod
    def calculate_rankings(bids: List[SupplierBidSummary]) -> List[RankedSupplier]:
        """
        Calculates supplier rankings based on each supplier's best (lowest) valid bid.
        Tie-breaker: Earlier submission time wins (FIFO).
        Returns sorted list with rank 1 (L1), 2 (L2), etc.
        """
        if not bids:
            return []

        # Find best (lowest amount, then earliest submitted_at) bid per supplier
        supplier_best_bids: Dict[int, SupplierBidSummary] = {}
        for b in bids:
            existing = supplier_best_bids.get(b.supplier_id)
            if existing is None:
                supplier_best_bids[b.supplier_id] = b
            else:
                # Lower total wins; if identical, earlier timestamp wins
                if (b.total_quote_amount < existing.total_quote_amount or
                   (b.total_quote_amount == existing.total_quote_amount and b.submitted_at < existing.submitted_at)):
                    supplier_best_bids[b.supplier_id] = b

        # Sort distinct suppliers by total_quote_amount ASC, submitted_at ASC, bid_id ASC (FIFO tie-breaker)
        sorted_summaries = sorted(
            supplier_best_bids.values(),
            key=lambda x: (x.total_quote_amount, x.submitted_at, x.bid_id)
        )

        ranked: List[RankedSupplier] = []
        for index, summary in enumerate(sorted_summaries, start=1):
            ranked.append(RankedSupplier(
                rank=index,
                supplier_id=summary.supplier_id,
                supplier_name=summary.supplier_name,
                total_quote_amount=summary.total_quote_amount,
                submitted_at=summary.submitted_at,
                carrier_name=summary.carrier_name,
                bid_id=summary.bid_id
            ))
        return ranked

    @classmethod
    def evaluate_extension(
        cls,
        trigger_mode: ExtensionTriggerMode | str,
        trigger_window_minutes: int,
        extension_duration_minutes: int,
        current_close_time: datetime,
        forced_close_time: datetime,
        submission_time: datetime,
        bids_before: List[SupplierBidSummary],
        new_bid: SupplierBidSummary,
        british_auction_enabled: bool = True,
    ) -> ExtensionEvaluationResult:
        """
        Evaluates whether a newly submitted valid bid triggers an auction extension.
        Modes:
        1. BID_RECEIVED: Any valid bid in the trigger window
        2. ANY_RANK_CHANGE: Any supplier rank change in the trigger window
        3. L1_RANK_CHANGE: Lowest bidder (L1) rank change in the trigger window
        Extensions never exceed forced_close_time.
        """
        mode_val = trigger_mode.value if isinstance(trigger_mode, ExtensionTriggerMode) else trigger_mode

        in_window = cls.is_in_trigger_window(
            current_close_time=current_close_time,
            trigger_window_minutes=trigger_window_minutes,
            submission_time=submission_time
        )

        # Compute rankings before and after
        rankings_before = cls.calculate_rankings(bids_before)
        rankings_after = cls.calculate_rankings(bids_before + [new_bid])

        # Map supplier_id -> rank
        rank_map_before = {r.supplier_id: r.rank for r in rankings_before}
        rank_map_after = {r.supplier_id: r.rank for r in rankings_after}

        supplier_rank_before = rank_map_before.get(new_bid.supplier_id)
        supplier_rank_after = rank_map_after.get(new_bid.supplier_id)

        # Check if L1 changed
        l1_before_id = rankings_before[0].supplier_id if rankings_before else None
        l1_after_id = rankings_after[0].supplier_id if rankings_after else None
        l1_changed = (l1_before_id != l1_after_id) and (l1_after_id is not None)

        # Check if any ranking changed
        rankings_changed = (rank_map_before != rank_map_after)

        if not british_auction_enabled:
            return ExtensionEvaluationResult(
                should_extend=False,
                trigger_mode=mode_val,
                is_in_window=in_window,
                previous_close_time=current_close_time,
                new_close_time=current_close_time,
                extension_minutes_applied=0,
                reason="British Auction dynamic extension disabled for this RFQ.",
                l1_changed=l1_changed,
                rankings_changed=rankings_changed,
                rank_before=supplier_rank_before,
                rank_after=supplier_rank_after,
            )

        # Evaluate trigger condition
        condition_met = False
        trigger_detail = ""

        if not in_window:
            trigger_detail = f"Bid submitted outside trigger window (remaining: {int((current_close_time - submission_time).total_seconds() / 60)}m, window: {trigger_window_minutes}m)."
        else:
            if mode_val == ExtensionTriggerMode.BID_RECEIVED.value:
                condition_met = True
                trigger_detail = (
                    f"Mode 1 [Bid Received]: Valid bid from {new_bid.supplier_name} "
                    f"received inside last {trigger_window_minutes}m."
                )

            elif mode_val == ExtensionTriggerMode.ANY_RANK_CHANGE.value:
                if rankings_changed:
                    condition_met = True
                    rank_from_str = f"L{supplier_rank_before}" if supplier_rank_before else "Unranked"
                    trigger_detail = (
                        f"Mode 2 [Any Rank Change]: Supplier ranking changed inside last {trigger_window_minutes}m. "
                        f"{new_bid.supplier_name} moved from {rank_from_str} to L{supplier_rank_after}."
                    )
                else:
                    trigger_detail = (
                        f"Mode 2 [Any Rank Change]: Bid accepted, but supplier rankings did not change."
                    )

            elif mode_val == ExtensionTriggerMode.L1_RANK_CHANGE.value:
                if l1_changed:
                    condition_met = True
                    prev_l1_name = rankings_before[0].supplier_name if rankings_before else "None"
                    trigger_detail = (
                        f"Mode 3 [L1 Rank Change]: Lowest bidder changed inside last {trigger_window_minutes}m! "
                        f"{new_bid.supplier_name} dethroned {prev_l1_name} for L1 position."
                    )
                else:
                    trigger_detail = (
                        f"Mode 3 [L1 Rank Change]: Bid accepted, but L1 (lowest bidder) remained unchanged."
                    )

        # Calculate extension if condition is met
        should_extend = False
        new_close = current_close_time
        applied_minutes = 0

        if condition_met:
            # Check if current_close_time is already at or past forced_close_time
            if current_close_time >= forced_close_time:
                trigger_detail += f" However, auction is already at forced close deadline ({forced_close_time.isoformat()}). Extension capped."
            else:
                proposed_close = current_close_time + timedelta(minutes=extension_duration_minutes)
                if proposed_close >= forced_close_time:
                    new_close = forced_close_time
                    applied_seconds = (forced_close_time - current_close_time).total_seconds()
                    applied_minutes = max(1, int(applied_seconds / 60))
                    should_extend = True
                    trigger_detail += (
                        f" Auction extended to FORCED CLOSE limit: {forced_close_time.isoformat()} "
                        f"(capped from full {extension_duration_minutes}m extension)."
                    )
                else:
                    new_close = proposed_close
                    applied_minutes = extension_duration_minutes
                    should_extend = True
                    trigger_detail += (
                        f" Auction extended by {extension_duration_minutes}m to {new_close.isoformat()}."
                    )

        return ExtensionEvaluationResult(
            should_extend=should_extend,
            trigger_mode=mode_val,
            is_in_window=in_window,
            previous_close_time=current_close_time,
            new_close_time=new_close,
            extension_minutes_applied=applied_minutes,
            reason=trigger_detail,
            l1_changed=l1_changed,
            rankings_changed=rankings_changed,
            rank_before=supplier_rank_before,
            rank_after=supplier_rank_after,
        )

    @staticmethod
    def determine_status(
        bid_start_time: datetime,
        current_close_time: datetime,
        forced_close_time: datetime,
        current_time: datetime,
        current_status: str
    ) -> AuctionStatus:
        """
        Evaluates authoritative status based on current time and close boundaries:
        - FORCE_CLOSED: current_time >= forced_close_time AND current_close_time >= forced_close_time
        - CLOSED: current_time >= current_close_time
        - ACTIVE: bid_start_time <= current_time < current_close_time
        - SCHEDULED: current_time < bid_start_time
        """
        if current_time >= forced_close_time and current_close_time >= forced_close_time:
            return AuctionStatus.FORCE_CLOSED

        if current_time >= current_close_time:
            return AuctionStatus.CLOSED

        if current_time >= bid_start_time:
            return AuctionStatus.ACTIVE

        return AuctionStatus.SCHEDULED
