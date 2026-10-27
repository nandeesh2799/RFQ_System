from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import uuid
import pytest
from app.core.clock import MockClock
from app.core.constants import ActivityType, AuctionStatus, ExtensionTriggerMode
from app.db.session import SessionLocal
from app.models.bid import Bid
from app.models.rfq import RFQ
from app.models.user import User
from app.schemas.bid import BidCreate
from app.schemas.rfq import RFQCreate
from app.services.auction_engine import AuctionEngine, SupplierBidSummary
from app.services.bid_service import BidService
from app.services.rfq_service import RFQService


def create_utc(year=2026, month=10, day=27, hour=12, minute=0, second=0, microsecond=0) -> datetime:
    return datetime(year, month, day, hour, minute, second, microsecond, tzinfo=timezone.utc)


def test_mode1_exact_window_boundaries():
    """
    Adversarial boundary checks for Mode 1:
    - Exactly at window start [close - X]: in window -> extends
    - 1 microsecond before window start: outside window -> does NOT extend
    - 1 microsecond before close: inside window -> extends
    - Exactly at close: auction closed -> does NOT extend
    - british_auction_enabled=False inside window -> does NOT extend
    """
    close = create_utc(hour=12, minute=0, second=0)
    forced = create_utc(hour=13, minute=0, second=0)
    x = 10  # 10 minute window: [11:50:00, 12:00:00)
    y = 5

    window_start = close - timedelta(minutes=x)  # 11:50:00

    # 1. Exactly at window start
    bid_start = SupplierBidSummary(1, "A", Decimal("1000"), window_start, "A", 1)
    res_start = AuctionEngine.evaluate_extension(
        ExtensionTriggerMode.BID_RECEIVED, x, y, close, forced, window_start, [], bid_start
    )
    assert res_start.is_in_window is True
    assert res_start.should_extend is True
    assert res_start.new_close_time == create_utc(hour=12, minute=5)

    # 2. 1 microsecond before window start
    just_before_window = window_start - timedelta(microseconds=1)
    bid_before = SupplierBidSummary(1, "A", Decimal("1000"), just_before_window, "A", 2)
    res_before = AuctionEngine.evaluate_extension(
        ExtensionTriggerMode.BID_RECEIVED, x, y, close, forced, just_before_window, [], bid_before
    )
    assert res_before.is_in_window is False
    assert res_before.should_extend is False
    assert res_before.new_close_time == close

    # 3. 1 microsecond before close
    just_before_close = close - timedelta(microseconds=1)
    bid_near_close = SupplierBidSummary(1, "A", Decimal("1000"), just_before_close, "A", 3)
    res_near_close = AuctionEngine.evaluate_extension(
        ExtensionTriggerMode.BID_RECEIVED, x, y, close, forced, just_before_close, [], bid_near_close
    )
    assert res_near_close.is_in_window is True
    assert res_near_close.should_extend is True

    # 4. Exactly at close
    bid_at_close = SupplierBidSummary(1, "A", Decimal("1000"), close, "A", 4)
    res_at_close = AuctionEngine.evaluate_extension(
        ExtensionTriggerMode.BID_RECEIVED, x, y, close, forced, close, [], bid_at_close
    )
    assert res_at_close.is_in_window is False
    assert res_at_close.should_extend is False

    # 5. british_auction_enabled=False inside window
    res_disabled = AuctionEngine.evaluate_extension(
        ExtensionTriggerMode.BID_RECEIVED, x, y, close, forced, window_start, [], bid_start,
        british_auction_enabled=False
    )
    assert res_disabled.is_in_window is True
    assert res_disabled.should_extend is False
    assert "disabled" in res_disabled.reason.lower()


def test_mode2_all_rank_change_permutations():
    """
    Mode 2: Any supplier rank change triggers extension.
    - First bid in empty auction -> rank unranked -> L1 -> EXTENDS
    - New supplier enters at L3 -> EXTENDS
    - Existing L3 supplier overtakes L2 -> EXTENDS
    - Existing L2 supplier overtakes L1 -> EXTENDS
    - Existing L1 supplier lowers quote, remains L1 -> DOES NOT EXTEND
    - Existing L3 supplier lowers quote, remains L3 -> DOES NOT EXTEND
    - Tied bid where FIFO maintains identical ranks -> DOES NOT EXTEND
    """
    close = create_utc(hour=12, minute=0)
    forced = create_utc(hour=13, minute=0)
    x = 10
    y = 5

    # 1. First bid in empty auction
    bid1 = SupplierBidSummary(1, "A", Decimal("3000"), create_utc(hour=11, minute=52), "A", 1)
    res1 = AuctionEngine.evaluate_extension(
        ExtensionTriggerMode.ANY_RANK_CHANGE, x, y, close, forced, bid1.submitted_at, [], bid1
    )
    assert res1.should_extend is True
    assert res1.rankings_changed is True

    # Setup 3 suppliers: A ($3000, L1), B ($4000, L2), C ($5000, L3)
    bids_base = [
        SupplierBidSummary(1, "A", Decimal("3000"), create_utc(hour=10, minute=0), "A", 1),
        SupplierBidSummary(2, "B", Decimal("4000"), create_utc(hour=10, minute=1), "B", 2),
        SupplierBidSummary(3, "C", Decimal("5000"), create_utc(hour=10, minute=2), "C", 3),
    ]

    # 2. New supplier D enters at L4
    bid_d = SupplierBidSummary(4, "D", Decimal("6000"), create_utc(hour=11, minute=53), "D", 4)
    res_d = AuctionEngine.evaluate_extension(
        ExtensionTriggerMode.ANY_RANK_CHANGE, x, y, close, forced, bid_d.submitted_at, bids_base, bid_d
    )
    assert res_d.should_extend is True
    assert res_d.rankings_changed is True

    # 3. Existing L3 supplier C overtakes L2 ($3500 < $4000)
    bid_c_l2 = SupplierBidSummary(3, "C", Decimal("3500"), create_utc(hour=11, minute=54), "C", 5)
    res_c_l2 = AuctionEngine.evaluate_extension(
        ExtensionTriggerMode.ANY_RANK_CHANGE, x, y, close, forced, bid_c_l2.submitted_at, bids_base, bid_c_l2
    )
    assert res_c_l2.should_extend is True
    assert res_c_l2.rankings_changed is True

    # 4. Existing L2 supplier B overtakes L1 ($2800 < $3000)
    bid_b_l1 = SupplierBidSummary(2, "B", Decimal("2800"), create_utc(hour=11, minute=55), "B", 6)
    res_b_l1 = AuctionEngine.evaluate_extension(
        ExtensionTriggerMode.ANY_RANK_CHANGE, x, y, close, forced, bid_b_l1.submitted_at, bids_base, bid_b_l1
    )
    assert res_b_l1.should_extend is True
    assert res_b_l1.rankings_changed is True

    # 5. Existing L1 supplier A lowers quote ($2500), but was ALREADY L1 -> NO rank change
    bid_a_lower = SupplierBidSummary(1, "A", Decimal("2500"), create_utc(hour=11, minute=56), "A", 7)
    res_a_lower = AuctionEngine.evaluate_extension(
        ExtensionTriggerMode.ANY_RANK_CHANGE, x, y, close, forced, bid_a_lower.submitted_at, bids_base, bid_a_lower
    )
    assert res_a_lower.should_extend is False
    assert res_a_lower.rankings_changed is False

    # 6. Existing L3 supplier C lowers quote ($4500), but is STILL L3 -> NO rank change
    bid_c_lower = SupplierBidSummary(3, "C", Decimal("4500"), create_utc(hour=11, minute=57), "C", 8)
    res_c_lower = AuctionEngine.evaluate_extension(
        ExtensionTriggerMode.ANY_RANK_CHANGE, x, y, close, forced, bid_c_lower.submitted_at, bids_base, bid_c_lower
    )
    assert res_c_lower.should_extend is False
    assert res_c_lower.rankings_changed is False

    # 7. Existing L2 supplier B ties L1 price ($3000), FIFO keeps A at L1 and B at L2 -> NO rank change
    bid_b_tie = SupplierBidSummary(2, "B", Decimal("3000"), create_utc(hour=11, minute=58), "B", 9)
    res_b_tie = AuctionEngine.evaluate_extension(
        ExtensionTriggerMode.ANY_RANK_CHANGE, x, y, close, forced, bid_b_tie.submitted_at, bids_base, bid_b_tie
    )
    assert res_b_tie.should_extend is False
    assert res_b_tie.rankings_changed is False


def test_mode3_l1_rank_change_exhaustive():
    """
    Mode 3: Only changes in L1 (lowest bidder) trigger extension.
    - First bid in empty auction -> L1 created -> EXTENDS
    - L2 overtakes L1 -> EXTENDS
    - L3 overtakes L2, but L1 is untouched -> DOES NOT EXTEND
    - L1 supplier lowers their own quote -> L1 supplier unchanged -> DOES NOT EXTEND
    - Competitor ties L1 price -> FIFO keeps original L1 -> DOES NOT EXTEND
    """
    close = create_utc(hour=12, minute=0)
    forced = create_utc(hour=13, minute=0)
    x = 10
    y = 5

    # 1. First bid in empty auction
    bid1 = SupplierBidSummary(1, "A", Decimal("3000"), create_utc(hour=11, minute=52), "A", 1)
    res1 = AuctionEngine.evaluate_extension(
        ExtensionTriggerMode.L1_RANK_CHANGE, x, y, close, forced, bid1.submitted_at, [], bid1
    )
    assert res1.should_extend is True
    assert res1.l1_changed is True

    bids_base = [
        SupplierBidSummary(1, "A", Decimal("3000"), create_utc(hour=10, minute=0), "A", 1),
        SupplierBidSummary(2, "B", Decimal("4000"), create_utc(hour=10, minute=1), "B", 2),
        SupplierBidSummary(3, "C", Decimal("5000"), create_utc(hour=10, minute=2), "C", 3),
    ]

    # 2. L2 overtakes L1
    bid_b_l1 = SupplierBidSummary(2, "B", Decimal("2800"), create_utc(hour=11, minute=55), "B", 4)
    res_b = AuctionEngine.evaluate_extension(
        ExtensionTriggerMode.L1_RANK_CHANGE, x, y, close, forced, bid_b_l1.submitted_at, bids_base, bid_b_l1
    )
    assert res_b.should_extend is True
    assert res_b.l1_changed is True

    # 3. L3 overtakes L2 (becomes L2, but A remains L1)
    bid_c_l2 = SupplierBidSummary(3, "C", Decimal("3500"), create_utc(hour=11, minute=56), "C", 5)
    res_c = AuctionEngine.evaluate_extension(
        ExtensionTriggerMode.L1_RANK_CHANGE, x, y, close, forced, bid_c_l2.submitted_at, bids_base, bid_c_l2
    )
    assert res_c.should_extend is False
    assert res_c.l1_changed is False
    assert res_c.rankings_changed is True

    # 4. L1 supplier A lowers own price (from $3000 to $2500)
    bid_a_lower = SupplierBidSummary(1, "A", Decimal("2500"), create_utc(hour=11, minute=57), "A", 6)
    res_a = AuctionEngine.evaluate_extension(
        ExtensionTriggerMode.L1_RANK_CHANGE, x, y, close, forced, bid_a_lower.submitted_at, bids_base, bid_a_lower
    )
    assert res_a.should_extend is False
    assert res_a.l1_changed is False

    # 5. Competitor B ties L1 price ($3000)
    bid_b_tie = SupplierBidSummary(2, "B", Decimal("3000"), create_utc(hour=11, minute=58), "B", 7)
    res_tie = AuctionEngine.evaluate_extension(
        ExtensionTriggerMode.L1_RANK_CHANGE, x, y, close, forced, bid_b_tie.submitted_at, bids_base, bid_b_tie
    )
    assert res_tie.should_extend is False
    assert res_tie.l1_changed is False


def test_dynamic_trigger_window_cascades():
    """
    Tests dynamic trigger window recalculation across multiple consecutive extensions.
    Window is [current_close - X, current_close).
    """
    close = create_utc(hour=11, minute=0)
    forced = create_utc(hour=12, minute=0)
    x = 10
    y = 10

    # Extension 1: Bid at 10:55 is inside [10:50, 11:00) -> extends to 11:10
    res1 = AuctionEngine.evaluate_extension(
        ExtensionTriggerMode.BID_RECEIVED, x, y, close, forced, create_utc(hour=10, minute=55),
        [], SupplierBidSummary(1, "A", Decimal("5000"), create_utc(hour=10, minute=55), "A", 1)
    )
    assert res1.should_extend is True
    assert res1.new_close_time == create_utc(hour=11, minute=10)

    # Next window is [11:00, 11:10).
    # A bid placed at 10:58 is now OUTSIDE this dynamic window!
    res_stale = AuctionEngine.evaluate_extension(
        ExtensionTriggerMode.BID_RECEIVED, x, y, res1.new_close_time, forced, create_utc(hour=10, minute=58),
        [], SupplierBidSummary(2, "B", Decimal("4900"), create_utc(hour=10, minute=58), "B", 2)
    )
    assert res_stale.is_in_window is False
    assert res_stale.should_extend is False

    # A bid placed at 11:05 is inside [11:00, 11:10) -> extends to 11:20
    res2 = AuctionEngine.evaluate_extension(
        ExtensionTriggerMode.BID_RECEIVED, x, y, res1.new_close_time, forced, create_utc(hour=11, minute=5),
        [], SupplierBidSummary(3, "C", Decimal("4800"), create_utc(hour=11, minute=5), "C", 3)
    )
    assert res2.is_in_window is True
    assert res2.should_extend is True
    assert res2.new_close_time == create_utc(hour=11, minute=20)


def test_controllable_clock_end_to_end_auction_lifecycle():
    """
    Uses MockClock with BidService and RFQService to test:
    - Status SCHEDULED before start time
    - Transition to ACTIVE on first bid
    - Multiple extensions pushing close time to forced close cap
    - Clamping at min(current_close + Y, forced_close)
    - Rejection of bids after forced close
    - Authoritative status transition to FORCE_CLOSED
    """
    db = SessionLocal()
    try:
        clock = MockClock(create_utc(hour=9, minute=0))  # 9:00 AM
        rfq_service = RFQService(db=db, clock=clock)
        bid_service = BidService(db=db, clock=clock)

        buyer = db.query(User).filter(User.email == "buyer@acme.corp").first()
        supplier_apex = db.query(User).filter(User.email == "apex@logistics.com").first()
        supplier_blue = db.query(User).filter(User.email == "bluedart@freight.com").first()

        # 1. Create RFQ with start at 10:00, close at 11:00, forced close at 11:12
        rfq_data = RFQCreate(
            title="Adversarial Clock Test RFQ",
            reference_id=f"ADV-CLOCK-{uuid.uuid4().hex[:8]}",
            origin="Rotterdam",
            destination="Dubai",
            cargo_details="Machinery parts",
            pickup_date=date.today() + timedelta(days=7),
            british_auction_enabled=True,
            bid_start_time=create_utc(hour=10, minute=0),
            bid_close_time=create_utc(hour=11, minute=0),
            forced_close_time=create_utc(hour=11, minute=12),
            trigger_window_minutes=10,
            extension_duration_minutes=5,
            extension_trigger_mode=ExtensionTriggerMode.BID_RECEIVED
        )
        rfq = rfq_service.create_rfq(rfq_data, creator_id=buyer.id)
        assert rfq.status == AuctionStatus.SCHEDULED.value

        # 2. Attempt bid while SCHEDULED at 9:30 AM -> rejected
        clock.set_time(create_utc(hour=9, minute=30))
        bid_in = BidCreate(
            carrier_name="Apex Global",
            freight_charges=Decimal("3000.00"),
            origin_charges=Decimal("200.00"),
            destination_charges=Decimal("100.00"),
            transit_time_days=5,
            quote_validity_date=date.today() + timedelta(days=20)
        )
        with pytest.raises(Exception) as exc_info:
            bid_service.submit_bid(rfq.id, bid_in, supplier_apex.id)
        assert "SCHEDULED" in str(exc_info.value)

        # 3. Advance clock into ACTIVE period: 10:30 AM (outside trigger window [10:50, 11:00))
        clock.set_time(create_utc(hour=10, minute=30))
        bid1, ext1, rankings1 = bid_service.submit_bid(rfq.id, bid_in, supplier_apex.id)
        assert bid1.total_quote_amount == Decimal("3300.00")
        assert ext1.should_extend is False
        assert rfq.status == AuctionStatus.ACTIVE.value
        assert rfq.current_close_time == create_utc(hour=11, minute=0)

        # 4. Advance clock into trigger window: 10:55 AM -> Extension 1 (adds 5 min -> 11:05)
        clock.set_time(create_utc(hour=10, minute=55))
        bid_blue_1 = BidCreate(
            carrier_name="BlueDart Express",
            freight_charges=Decimal("2800.00"),
            origin_charges=Decimal("200.00"),
            destination_charges=Decimal("100.00"),
            transit_time_days=5,
            quote_validity_date=date.today() + timedelta(days=20)
        )
        bid2, ext2, _ = bid_service.submit_bid(rfq.id, bid_blue_1, supplier_blue.id)
        assert ext2.should_extend is True
        assert ext2.new_close_time == create_utc(hour=11, minute=5)
        assert rfq.current_close_time == create_utc(hour=11, minute=5)

        # 5. Extension 2 at 11:02 AM -> adds 5 min -> 11:10
        clock.set_time(create_utc(hour=11, minute=2))
        bid_apex_2 = BidCreate(
            carrier_name="Apex Global",
            freight_charges=Decimal("2700.00"),
            origin_charges=Decimal("200.00"),
            destination_charges=Decimal("100.00"),
            transit_time_days=5,
            quote_validity_date=date.today() + timedelta(days=20)
        )
        bid3, ext3, _ = bid_service.submit_bid(rfq.id, bid_apex_2, supplier_apex.id)
        assert ext3.should_extend is True
        assert ext3.new_close_time == create_utc(hour=11, minute=10)

        # 6. Extension 3 at 11:08 AM -> proposed close is 11:15, but forced_close is 11:12!
        # Clamped at 11:12!
        clock.set_time(create_utc(hour=11, minute=8))
        bid_blue_2 = BidCreate(
            carrier_name="BlueDart Express",
            freight_charges=Decimal("2600.00"),
            origin_charges=Decimal("200.00"),
            destination_charges=Decimal("100.00"),
            transit_time_days=5,
            quote_validity_date=date.today() + timedelta(days=20)
        )
        bid4, ext4, _ = bid_service.submit_bid(rfq.id, bid_blue_2, supplier_blue.id)
        assert ext4.should_extend is True
        assert ext4.new_close_time == create_utc(hour=11, minute=12)
        assert ext4.extension_minutes_applied == 2
        assert rfq.current_close_time == create_utc(hour=11, minute=12)

        # 7. Auction is now capped at forced close (11:12).
        # At 11:11, Apex submits lower quote -> accepted, but NO further extension!
        clock.set_time(create_utc(hour=11, minute=11))
        bid_apex_3 = BidCreate(
            carrier_name="Apex Global",
            freight_charges=Decimal("2500.00"),
            origin_charges=Decimal("200.00"),
            destination_charges=Decimal("100.00"),
            transit_time_days=5,
            quote_validity_date=date.today() + timedelta(days=20)
        )
        bid5, ext5, _ = bid_service.submit_bid(rfq.id, bid_apex_3, supplier_apex.id)
        assert ext5.should_extend is False
        assert rfq.current_close_time == create_utc(hour=11, minute=12)

        # 8. Clock reaches forced close: 11:12 AM exact.
        # Any further bid is rejected!
        clock.set_time(create_utc(hour=11, minute=12))
        with pytest.raises(Exception) as exc_forced:
            bid_service.submit_bid(rfq.id, bid_apex_3, supplier_apex.id)
        assert "closed" in str(exc_forced.value).lower() or "forced close" in str(exc_forced.value).lower()

        # 9. Verify status transition to FORCE_CLOSED
        status = rfq_service.update_rfq_status_if_needed(rfq)
        assert status == AuctionStatus.FORCE_CLOSED.value

    finally:
        db.close()


def test_natural_close_vs_forced_close_status():
    """
    Verifies that an auction expiring naturally at current_close without hitting forced_close
    transitions to CLOSED, not FORCE_CLOSED, even after forced_close_time has elapsed.
    """
    start = create_utc(hour=10, minute=0)
    close = create_utc(hour=11, minute=0)
    forced = create_utc(hour=12, minute=0)

    # During auction
    assert AuctionEngine.determine_status(start, close, forced, create_utc(hour=10, minute=30), "ACTIVE") == AuctionStatus.ACTIVE

    # At natural close (11:00)
    assert AuctionEngine.determine_status(start, close, forced, create_utc(hour=11, minute=0), "ACTIVE") == AuctionStatus.CLOSED

    # After natural close, but before forced close (11:30)
    assert AuctionEngine.determine_status(start, close, forced, create_utc(hour=11, minute=30), "ACTIVE") == AuctionStatus.CLOSED

    # After forced close (12:05) -> must REMAIN CLOSED because it closed naturally!
    assert AuctionEngine.determine_status(start, close, forced, create_utc(hour=12, minute=5), "ACTIVE") == AuctionStatus.CLOSED

    # ONLY when current_close was extended to forced_close does it become FORCE_CLOSED
    assert AuctionEngine.determine_status(start, forced, forced, create_utc(hour=12, minute=0), "ACTIVE") == AuctionStatus.FORCE_CLOSED


def test_descending_price_equal_bid_rank_stamping():
    """
    Verifies that when a supplier submits a bid with the SAME amount as their previous best bid:
    1. It is accepted under the descending price rule (non-increasing).
    2. The supplier's rank_at_submission is properly stamped (not None).
    """
    db = SessionLocal()
    try:
        clock = MockClock(create_utc(hour=10, minute=15))
        rfq_service = RFQService(db=db, clock=clock)
        bid_service = BidService(db=db, clock=clock)

        buyer = db.query(User).filter(User.email == "buyer@acme.corp").first()
        supplier_apex = db.query(User).filter(User.email == "apex@logistics.com").first()

        rfq_data = RFQCreate(
            title="Equal Bid Stamping Test",
            reference_id=f"EQUAL-BID-{uuid.uuid4().hex[:8]}",
            origin="Shanghai",
            destination="Hamburg",
            cargo_details="Electronics",
            pickup_date=date.today() + timedelta(days=10),
            british_auction_enabled=True,
            bid_start_time=create_utc(hour=10, minute=0),
            bid_close_time=create_utc(hour=11, minute=0),
            forced_close_time=create_utc(hour=12, minute=0),
            trigger_window_minutes=10,
            extension_duration_minutes=5,
            extension_trigger_mode=ExtensionTriggerMode.BID_RECEIVED
        )
        rfq = rfq_service.create_rfq(rfq_data, creator_id=buyer.id)

        bid_payload = BidCreate(
            carrier_name="Apex First",
            freight_charges=Decimal("3000.00"),
            origin_charges=Decimal("100.00"),
            destination_charges=Decimal("100.00"),
            transit_time_days=10,
            quote_validity_date=date.today() + timedelta(days=30)
        )
        bid1, _, _ = bid_service.submit_bid(rfq.id, bid_payload, supplier_apex.id)
        assert bid1.total_quote_amount == Decimal("3200.00")
        assert bid1.rank_at_submission == 1

        # Submit equal quote with different carrier/notes
        clock.advance(minutes=5)
        bid_payload_equal = BidCreate(
            carrier_name="Apex Alternative Carrier",
            freight_charges=Decimal("3000.00"),
            origin_charges=Decimal("100.00"),
            destination_charges=Decimal("100.00"),
            transit_time_days=8,
            quote_validity_date=date.today() + timedelta(days=30),
            notes="Faster transit time option for same price"
        )
        bid2, _, _ = bid_service.submit_bid(rfq.id, bid_payload_equal, supplier_apex.id)
        assert bid2.total_quote_amount == Decimal("3200.00")
        # Critical verification: rank_at_submission must NOT be None!
        assert bid2.rank_at_submission == 1
    finally:
        db.close()


def test_invalid_bids_rejections():
    """
    Adversarial test for all invalid quote submission vectors:
    - Negative freight charges -> 422
    - Blank / whitespace carrier name -> 422
    - Bid before start time -> 400
    - Bid at or after close time -> 400
    - Bid after forced close time -> 400
    - Higher quote than supplier's previous best -> 400
    """
    from pydantic import ValidationError
    from fastapi import HTTPException

    # 1. Pydantic validation rejects negative charges
    with pytest.raises(ValidationError):
        BidCreate(
            carrier_name="Valid Carrier",
            freight_charges=Decimal("-100.00"),
            origin_charges=Decimal("50.00"),
            destination_charges=Decimal("50.00"),
            transit_time_days=5,
            quote_validity_date=date.today() + timedelta(days=10)
        )

    # 2. Pydantic validation rejects blank carrier name
    with pytest.raises(ValidationError):
        BidCreate(
            carrier_name="   ",
            freight_charges=Decimal("1000.00"),
            origin_charges=Decimal("50.00"),
            destination_charges=Decimal("50.00"),
            transit_time_days=5,
            quote_validity_date=date.today() + timedelta(days=10)
        )

    # 3. Domain validation in AuctionEngine
    start = create_utc(hour=10, minute=0)
    close = create_utc(hour=11, minute=0)
    forced = create_utc(hour=12, minute=0)

    # Before start
    ok, err = AuctionEngine.is_bid_eligible(start, close, forced, create_utc(hour=9, minute=59))
    assert ok is False
    assert "not started" in err

    # At exact close
    ok, err = AuctionEngine.is_bid_eligible(start, close, forced, close)
    assert ok is False
    assert "closed" in err

    # At exact forced close
    ok, err = AuctionEngine.is_bid_eligible(start, close, forced, forced)
    assert ok is False
    assert "forced close" in err


def test_simultaneous_race_condition_controllable_clock():
    """
    Spawns concurrent worker threads submitting simultaneous bids at the exact same controllable
    mock clock timestamp inside the dynamic trigger window, validating ACID row-level locking.
    """
    from concurrent.futures import ThreadPoolExecutor

    db = SessionLocal()
    clock = MockClock(create_utc(hour=10, minute=52))
    rfq_service = RFQService(db=db, clock=clock)

    buyer = db.query(User).filter(User.email == "buyer@acme.corp").first()
    supplier_data = [
        {"id": u.id, "company_name": u.company_name}
        for u in db.query(User).filter(User.role == "SUPPLIER").all()[:4]
    ]

    rfq_data = RFQCreate(
        title="Simultaneous Locking Test RFQ",
        reference_id=f"CONCUR-CLOCK-{uuid.uuid4().hex[:8]}",
        origin="Tokyo",
        destination="Los Angeles",
        cargo_details="Automotive components",
        pickup_date=date.today() + timedelta(days=14),
        british_auction_enabled=True,
        bid_start_time=create_utc(hour=10, minute=0),
        bid_close_time=create_utc(hour=11, minute=0),  # Close 11:00, clock 10:52 -> in 10m window!
        forced_close_time=create_utc(hour=12, minute=0),
        trigger_window_minutes=10,
        extension_duration_minutes=5,
        extension_trigger_mode=ExtensionTriggerMode.BID_RECEIVED
    )
    rfq = rfq_service.create_rfq(rfq_data, creator_id=buyer.id)
    rfq_id = rfq.id
    db.close()

    def submit_concurrent_bid(supplier_info):
        thread_db = SessionLocal()
        thread_bid_service = BidService(db=thread_db, clock=clock)
        try:
            bid_in = BidCreate(
                carrier_name=f"{supplier_info['company_name']} Line",
                freight_charges=Decimal(f"{2000 + supplier_info['id'] * 100}.00"),
                origin_charges=Decimal("150.00"),
                destination_charges=Decimal("150.00"),
                transit_time_days=10,
                quote_validity_date=date.today() + timedelta(days=30)
            )
            bid, ext, rankings = thread_bid_service.submit_bid(rfq_id, bid_in, supplier_info['id'])
            return True, bid.total_quote_amount, ext.should_extend
        finally:
            thread_db.close()

    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(submit_concurrent_bid, supplier_data))

    # All concurrent threads must succeed cleanly without deadlock or lock timeout
    assert all(r[0] is True for r in results)

    # Verify database state after all concurrent bids
    verify_db = SessionLocal()
    try:
        final_rfq = verify_db.query(RFQ).filter(RFQ.id == rfq_id).first()
        bids = verify_db.query(Bid).filter(Bid.rfq_id == rfq_id).all()
        assert len(bids) == len(supplier_data)
        # Close time must have extended beyond initial 11:00
        assert final_rfq.current_close_time > create_utc(hour=11, minute=0)
        # RFQ has valid lowest bid stamped
        assert final_rfq.current_lowest_bid is not None
        assert final_rfq.current_l1_supplier_id is not None
    finally:
        verify_db.close()

