from datetime import datetime, timedelta, timezone
from decimal import Decimal
import pytest
from app.core.clock import MockClock
from app.core.constants import AuctionStatus, ExtensionTriggerMode
from app.services.auction_engine import AuctionEngine, SupplierBidSummary


def create_utc(hour: int, minute: int, second: int = 0) -> datetime:
    return datetime(2026, 10, 27, hour, minute, second, tzinfo=timezone.utc)


def test_dynamic_trigger_window_advancement():
    """
    Verifies that when an extension occurs, the trigger window dynamically advances
    relative to the new close time, rather than being stuck on the static initial close time.
    """
    initial_close = create_utc(12, 0)
    forced_close = create_utc(13, 0)
    x = 10  # 10 minute trigger window
    y = 5   # 5 minute extension

    # 1. First bid at 11:52:00 (inside initial window 11:50 - 12:00)
    bid1 = SupplierBidSummary(
        supplier_id=1,
        supplier_name="Carrier 1",
        total_quote_amount=Decimal("5000.00"),
        submitted_at=create_utc(11, 52),
        carrier_name="Carrier 1",
        bid_id=1
    )
    res1 = AuctionEngine.evaluate_extension(
        trigger_mode=ExtensionTriggerMode.BID_RECEIVED,
        trigger_window_minutes=x,
        extension_duration_minutes=y,
        current_close_time=initial_close,
        forced_close_time=forced_close,
        submission_time=bid1.submitted_at,
        bids_before=[],
        new_bid=bid1
    )
    assert res1.should_extend is True
    assert res1.new_close_time == create_utc(12, 5)

    # 2. After extension, new close is 12:05.
    # The new trigger window is [11:55, 12:05).
    # A subsequent bid at 11:54 is now BEFORE the new trigger window!
    bid2_early = SupplierBidSummary(
        supplier_id=2,
        supplier_name="Carrier 2",
        total_quote_amount=Decimal("4900.00"),
        submitted_at=create_utc(11, 54),
        carrier_name="Carrier 2",
        bid_id=2
    )
    res2_early = AuctionEngine.evaluate_extension(
        trigger_mode=ExtensionTriggerMode.BID_RECEIVED,
        trigger_window_minutes=x,
        extension_duration_minutes=y,
        current_close_time=res1.new_close_time,  # 12:05
        forced_close_time=forced_close,
        submission_time=bid2_early.submitted_at,
        bids_before=[bid1],
        new_bid=bid2_early
    )
    # 11:54 is outside [11:55, 12:05) -> should NOT extend!
    assert res2_early.should_extend is False

    # 3. A subsequent bid at 11:58 is inside the new window [11:55, 12:05) -> extends to 12:10!
    bid3_inside = SupplierBidSummary(
        supplier_id=3,
        supplier_name="Carrier 3",
        total_quote_amount=Decimal("4800.00"),
        submitted_at=create_utc(11, 58),
        carrier_name="Carrier 3",
        bid_id=3
    )
    res3 = AuctionEngine.evaluate_extension(
        trigger_mode=ExtensionTriggerMode.BID_RECEIVED,
        trigger_window_minutes=x,
        extension_duration_minutes=y,
        current_close_time=res1.new_close_time,  # 12:05
        forced_close_time=forced_close,
        submission_time=bid3_inside.submitted_at,
        bids_before=[bid1, bid2_early],
        new_bid=bid3_inside
    )
    assert res3.should_extend is True
    assert res3.new_close_time == create_utc(12, 10)


def test_repeated_extensions_hit_forced_close_ceiling():
    """
    Simulates consecutive rapid extensions driving close time into the forced close cap.
    """
    current_close = create_utc(12, 0)
    forced_close = create_utc(12, 12)  # Cap is 12 minutes after initial close
    x = 10
    y = 5

    # Extension 1: 12:00 + 5m = 12:05
    res1 = AuctionEngine.evaluate_extension(
        trigger_mode=ExtensionTriggerMode.BID_RECEIVED,
        trigger_window_minutes=x,
        extension_duration_minutes=y,
        current_close_time=current_close,
        forced_close_time=forced_close,
        submission_time=create_utc(11, 55),
        bids_before=[],
        new_bid=SupplierBidSummary(1, "A", Decimal("5000"), create_utc(11, 55), "A", 1)
    )
    assert res1.new_close_time == create_utc(12, 5)

    # Extension 2: 12:05 + 5m = 12:10
    res2 = AuctionEngine.evaluate_extension(
        trigger_mode=ExtensionTriggerMode.BID_RECEIVED,
        trigger_window_minutes=x,
        extension_duration_minutes=y,
        current_close_time=res1.new_close_time,
        forced_close_time=forced_close,
        submission_time=create_utc(12, 2),
        bids_before=[],
        new_bid=SupplierBidSummary(2, "B", Decimal("4900"), create_utc(12, 2), "B", 2)
    )
    assert res2.new_close_time == create_utc(12, 10)

    # Extension 3: 12:10 + 5m = 12:15, but forced_close is 12:12 -> Clamped at 12:12!
    res3 = AuctionEngine.evaluate_extension(
        trigger_mode=ExtensionTriggerMode.BID_RECEIVED,
        trigger_window_minutes=x,
        extension_duration_minutes=y,
        current_close_time=res2.new_close_time,
        forced_close_time=forced_close,
        submission_time=create_utc(12, 8),
        bids_before=[],
        new_bid=SupplierBidSummary(3, "C", Decimal("4800"), create_utc(12, 8), "C", 3)
    )
    assert res3.should_extend is True
    assert res3.new_close_time == forced_close  # Exactly 12:12
    assert res3.extension_minutes_applied == 2

    # Extension 4: Auction is already at forced_close (12:12).
    # Any further bids must NOT extend further!
    res4 = AuctionEngine.evaluate_extension(
        trigger_mode=ExtensionTriggerMode.BID_RECEIVED,
        trigger_window_minutes=x,
        extension_duration_minutes=y,
        current_close_time=forced_close,
        forced_close_time=forced_close,
        submission_time=create_utc(12, 11),
        bids_before=[],
        new_bid=SupplierBidSummary(4, "D", Decimal("4700"), create_utc(12, 11), "D", 4)
    )
    assert res4.should_extend is False
    assert res4.new_close_time == forced_close


def test_mode_3_intermediate_rank_changes_do_not_extend():
    """
    In Mode 3, an L2/L3 rank change must NOT trigger an extension.
    Only dethroning L1 can trigger extension.
    """
    close = create_utc(12, 0)
    forced = create_utc(13, 0)
    x = 10
    y = 5

    bids_before = [
        SupplierBidSummary(1, "A", Decimal("2000.00"), create_utc(10, 0), "A", 1),  # L1
        SupplierBidSummary(2, "B", Decimal("3000.00"), create_utc(10, 5), "B", 2),  # L2
        SupplierBidSummary(3, "C", Decimal("4000.00"), create_utc(10, 10), "C", 3), # L3
        SupplierBidSummary(4, "D", Decimal("5000.00"), create_utc(10, 15), "D", 4), # L4
    ]

    # Supplier D submits 3500 -> Overtakes C (4000) for L3.
    # L1 (A at 2000) is unchanged. Mode 3 must NOT extend.
    bid_d = SupplierBidSummary(4, "D", Decimal("3500.00"), create_utc(11, 55), "D", 5)
    res_d = AuctionEngine.evaluate_extension(
        trigger_mode=ExtensionTriggerMode.L1_RANK_CHANGE,
        trigger_window_minutes=x,
        extension_duration_minutes=y,
        current_close_time=close,
        forced_close_time=forced,
        submission_time=bid_d.submitted_at,
        bids_before=bids_before,
        new_bid=bid_d
    )
    assert res_d.should_extend is False
    assert res_d.l1_changed is False
    assert res_d.rankings_changed is True

    # Supplier B submits 1950 -> Dethrones Supplier A (2000) for L1!
    # Mode 3 MUST extend!
    bid_b_l1 = SupplierBidSummary(2, "B", Decimal("1950.00"), create_utc(11, 56), "B", 6)
    res_l1 = AuctionEngine.evaluate_extension(
        trigger_mode=ExtensionTriggerMode.L1_RANK_CHANGE,
        trigger_window_minutes=x,
        extension_duration_minutes=y,
        current_close_time=close,
        forced_close_time=forced,
        submission_time=bid_b_l1.submitted_at,
        bids_before=bids_before + [bid_d],
        new_bid=bid_b_l1
    )
    assert res_l1.should_extend is True
    assert res_l1.l1_changed is True
    assert res_l1.new_close_time == create_utc(12, 5)


def test_fifo_tie_breaking_multiple_identical_quotes():
    """
    When 4 suppliers submit identical quotes, FIFO submission ordering strictly dictates L1, L2, L3, L4.
    """
    t1 = create_utc(10, 0, 1)
    t2 = create_utc(10, 0, 2)
    t3 = create_utc(10, 0, 3)
    t4 = create_utc(10, 0, 4)

    bids = [
        SupplierBidSummary(4, "Carrier 4", Decimal("3000.00"), t4, "C4", 4),
        SupplierBidSummary(2, "Carrier 2", Decimal("3000.00"), t2, "C2", 2),
        SupplierBidSummary(1, "Carrier 1", Decimal("3000.00"), t1, "C1", 1),
        SupplierBidSummary(3, "Carrier 3", Decimal("3000.00"), t3, "C3", 3),
    ]

    rankings = AuctionEngine.calculate_rankings(bids)
    assert [r.supplier_id for r in rankings] == [1, 2, 3, 4]
    assert [r.rank for r in rankings] == [1, 2, 3, 4]
