from datetime import datetime, timedelta, timezone
from decimal import Decimal
import pytest
from app.core.constants import AuctionStatus, ExtensionTriggerMode
from app.services.auction_engine import AuctionEngine, SupplierBidSummary


def create_utc(year=2026, month=10, day=27, hour=12, minute=0, second=0) -> datetime:
    return datetime(year, month, day, hour, minute, second, tzinfo=timezone.utc)


def test_quote_total_calculation():
    total = AuctionEngine.calculate_total_quote(
        freight_charges=Decimal("3500.50"),
        origin_charges=Decimal("450.25"),
        destination_charges=Decimal("300.00")
    )
    assert total == Decimal("4250.75")


def test_quote_total_rejects_negative():
    with pytest.raises(ValueError, match="negative"):
        AuctionEngine.calculate_total_quote(
            freight_charges=Decimal("-100"),
            origin_charges=Decimal("50"),
            destination_charges=Decimal("50")
        )


def test_rankings_and_fifo_tie_breaking():
    t1 = create_utc(hour=10, minute=0)
    t2 = create_utc(hour=10, minute=5)
    t3 = create_utc(hour=10, minute=10)

    bids = [
        SupplierBidSummary(supplier_id=1, supplier_name="Carrier A", total_quote_amount=Decimal("5000.00"), submitted_at=t1, carrier_name="A", bid_id=101),
        SupplierBidSummary(supplier_id=2, supplier_name="Carrier B", total_quote_amount=Decimal("4500.00"), submitted_at=t2, carrier_name="B", bid_id=102),
        SupplierBidSummary(supplier_id=3, supplier_name="Carrier C", total_quote_amount=Decimal("4500.00"), submitted_at=t3, carrier_name="C", bid_id=103),
    ]

    rankings = AuctionEngine.calculate_rankings(bids)
    assert len(rankings) == 3

    # Carrier B and C both quoted 4500.00, but B submitted earlier (t2 < t3) -> B is L1, C is L2, A is L3
    assert rankings[0].supplier_id == 2
    assert rankings[0].rank == 1
    assert rankings[1].supplier_id == 3
    assert rankings[1].rank == 2
    assert rankings[2].supplier_id == 1
    assert rankings[2].rank == 3


def test_is_bid_eligible_boundaries():
    start = create_utc(hour=10, minute=0)
    close = create_utc(hour=12, minute=0)
    forced = create_utc(hour=13, minute=0)

    # Before start
    eligible, reason = AuctionEngine.is_bid_eligible(start, close, forced, create_utc(hour=9, minute=59, second=59))
    assert eligible is False
    assert "not started" in reason

    # At exact start
    eligible, _ = AuctionEngine.is_bid_eligible(start, close, forced, start)
    assert eligible is True

    # 1 second before close
    eligible, _ = AuctionEngine.is_bid_eligible(start, close, forced, create_utc(hour=11, minute=59, second=59))
    assert eligible is True

    # At exact close
    eligible, reason = AuctionEngine.is_bid_eligible(start, close, forced, close)
    assert eligible is False
    assert "closed" in reason

    # After close but before forced close
    eligible, _ = AuctionEngine.is_bid_eligible(start, close, forced, create_utc(hour=12, minute=1))
    assert eligible is False

    # At forced close
    eligible, reason = AuctionEngine.is_bid_eligible(start, close, forced, forced)
    assert eligible is False
    assert "forced close" in reason


def test_trigger_window_calculation():
    close = create_utc(hour=12, minute=0)
    x = 10  # Window: 11:50 to 12:00

    assert AuctionEngine.is_in_trigger_window(close, x, create_utc(hour=11, minute=49, second=59)) is False
    assert AuctionEngine.is_in_trigger_window(close, x, create_utc(hour=11, minute=50, second=0)) is True
    assert AuctionEngine.is_in_trigger_window(close, x, create_utc(hour=11, minute=59, second=59)) is True
    assert AuctionEngine.is_in_trigger_window(close, x, create_utc(hour=12, minute=0, second=0)) is False


def test_trigger_mode_1_bid_received():
    close = create_utc(hour=12, minute=0)
    forced = create_utc(hour=13, minute=0)
    x = 10
    y = 5

    # Bid at 11:55 (inside last 10m)
    new_bid = SupplierBidSummary(supplier_id=2, supplier_name="Carrier B", total_quote_amount=Decimal("6000.00"), submitted_at=create_utc(hour=11, minute=55), carrier_name="B", bid_id=2)
    res = AuctionEngine.evaluate_extension(
        trigger_mode=ExtensionTriggerMode.BID_RECEIVED,
        trigger_window_minutes=x,
        extension_duration_minutes=y,
        current_close_time=close,
        forced_close_time=forced,
        submission_time=new_bid.submitted_at,
        bids_before=[],
        new_bid=new_bid
    )
    assert res.should_extend is True
    assert res.new_close_time == create_utc(hour=12, minute=5)
    assert res.extension_minutes_applied == 5


def test_trigger_mode_2_any_rank_change():
    close = create_utc(hour=12, minute=0)
    forced = create_utc(hour=13, minute=0)
    x = 10
    y = 5

    existing_bids = [
        SupplierBidSummary(supplier_id=1, supplier_name="Carrier A", total_quote_amount=Decimal("5000.00"), submitted_at=create_utc(hour=10, minute=0), carrier_name="A", bid_id=1),
        SupplierBidSummary(supplier_id=2, supplier_name="Carrier B", total_quote_amount=Decimal("6000.00"), submitted_at=create_utc(hour=10, minute=10), carrier_name="B", bid_id=2),
    ]

    # Carrier B submits 4800 at 11:58 -> Carrier B jumps from L2 to L1! Rank changes!
    new_bid = SupplierBidSummary(supplier_id=2, supplier_name="Carrier B", total_quote_amount=Decimal("4800.00"), submitted_at=create_utc(hour=11, minute=58), carrier_name="B", bid_id=3)
    res = AuctionEngine.evaluate_extension(
        trigger_mode=ExtensionTriggerMode.ANY_RANK_CHANGE,
        trigger_window_minutes=x,
        extension_duration_minutes=y,
        current_close_time=close,
        forced_close_time=forced,
        submission_time=new_bid.submitted_at,
        bids_before=existing_bids,
        new_bid=new_bid
    )
    assert res.should_extend is True
    assert res.rankings_changed is True
    assert res.new_close_time == create_utc(hour=12, minute=5)

    # Conversely, Carrier B submits 5500 at 11:58 -> Still rank 2 (Carrier A is 5000) -> No rank change!
    no_change_bid = SupplierBidSummary(supplier_id=2, supplier_name="Carrier B", total_quote_amount=Decimal("5500.00"), submitted_at=create_utc(hour=11, minute=58), carrier_name="B", bid_id=4)
    res_no_change = AuctionEngine.evaluate_extension(
        trigger_mode=ExtensionTriggerMode.ANY_RANK_CHANGE,
        trigger_window_minutes=x,
        extension_duration_minutes=y,
        current_close_time=close,
        forced_close_time=forced,
        submission_time=no_change_bid.submitted_at,
        bids_before=existing_bids,
        new_bid=no_change_bid
    )
    assert res_no_change.should_extend is False
    assert res_no_change.rankings_changed is False
    assert res_no_change.new_close_time == close


def test_trigger_mode_3_l1_rank_change():
    close = create_utc(hour=12, minute=0)
    forced = create_utc(hour=13, minute=0)
    x = 10
    y = 5

    existing_bids = [
        SupplierBidSummary(supplier_id=1, supplier_name="Carrier A", total_quote_amount=Decimal("3000.00"), submitted_at=create_utc(hour=10, minute=0), carrier_name="A", bid_id=1),
        SupplierBidSummary(supplier_id=2, supplier_name="Carrier B", total_quote_amount=Decimal("5000.00"), submitted_at=create_utc(hour=10, minute=10), carrier_name="B", bid_id=2),
        SupplierBidSummary(supplier_id=3, supplier_name="Carrier C", total_quote_amount=Decimal("6000.00"), submitted_at=create_utc(hour=10, minute=20), carrier_name="C", bid_id=3),
    ]

    # Carrier C quotes 4000 -> Overtakes Carrier B (5000) for L2, but Carrier A (3000) is STILL L1!
    # Mode 3 must NOT extend!
    bid_c = SupplierBidSummary(supplier_id=3, supplier_name="Carrier C", total_quote_amount=Decimal("4000.00"), submitted_at=create_utc(hour=11, minute=56), carrier_name="C", bid_id=4)
    res_c = AuctionEngine.evaluate_extension(
        trigger_mode=ExtensionTriggerMode.L1_RANK_CHANGE,
        trigger_window_minutes=x,
        extension_duration_minutes=y,
        current_close_time=close,
        forced_close_time=forced,
        submission_time=bid_c.submitted_at,
        bids_before=existing_bids,
        new_bid=bid_c
    )
    assert res_c.should_extend is False
    assert res_c.l1_changed is False
    assert res_c.rankings_changed is True

    # Carrier B quotes 2800 -> Dethrones Carrier A for L1!
    # Mode 3 MUST extend!
    bid_b_l1 = SupplierBidSummary(supplier_id=2, supplier_name="Carrier B", total_quote_amount=Decimal("2800.00"), submitted_at=create_utc(hour=11, minute=57), carrier_name="B", bid_id=5)
    res_l1 = AuctionEngine.evaluate_extension(
        trigger_mode=ExtensionTriggerMode.L1_RANK_CHANGE,
        trigger_window_minutes=x,
        extension_duration_minutes=y,
        current_close_time=close,
        forced_close_time=forced,
        submission_time=bid_b_l1.submitted_at,
        bids_before=existing_bids,
        new_bid=bid_b_l1
    )
    assert res_l1.should_extend is True
    assert res_l1.l1_changed is True
    assert res_l1.new_close_time == create_utc(hour=12, minute=5)


def test_forced_close_capping():
    close = create_utc(hour=12, minute=0)
    forced = create_utc(hour=12, minute=3)  # Only 3 minutes until forced close!
    x = 10
    y = 5  # Normally adds 5 minutes, which would be 12:05

    new_bid = SupplierBidSummary(supplier_id=1, supplier_name="Carrier A", total_quote_amount=Decimal("4000.00"), submitted_at=create_utc(hour=11, minute=58), carrier_name="A", bid_id=1)
    res = AuctionEngine.evaluate_extension(
        trigger_mode=ExtensionTriggerMode.BID_RECEIVED,
        trigger_window_minutes=x,
        extension_duration_minutes=y,
        current_close_time=close,
        forced_close_time=forced,
        submission_time=new_bid.submitted_at,
        bids_before=[],
        new_bid=new_bid
    )
    assert res.should_extend is True
    # Clamped at 12:03!
    assert res.new_close_time == forced
    assert res.extension_minutes_applied == 3
    assert "capped" in res.reason.lower()


def test_auction_status_determination():
    start = create_utc(hour=10, minute=0)
    close = create_utc(hour=12, minute=0)
    forced = create_utc(hour=13, minute=0)

    # Before start -> SCHEDULED
    assert AuctionEngine.determine_status(start, close, forced, create_utc(hour=9, minute=0), "SCHEDULED") == AuctionStatus.SCHEDULED

    # Active window -> ACTIVE
    assert AuctionEngine.determine_status(start, close, forced, create_utc(hour=11, minute=0), "ACTIVE") == AuctionStatus.ACTIVE

    # Reached normal close before forced close -> CLOSED
    assert AuctionEngine.determine_status(start, close, forced, create_utc(hour=12, minute=1), "ACTIVE") == AuctionStatus.CLOSED

    # Reached forced close when close time was pushed to forced close -> FORCE_CLOSED
    assert AuctionEngine.determine_status(start, forced, forced, create_utc(hour=13, minute=1), "ACTIVE") == AuctionStatus.FORCE_CLOSED
