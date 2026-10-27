import os
import sys
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

# Ensure backend path is on sys.path
for candidate in [
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")),
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..")),
    os.path.abspath("backend"),
    os.path.abspath(".")
]:
    if os.path.isdir(os.path.join(candidate, "app")) and candidate not in sys.path:
        sys.path.insert(0, candidate)

from app.core.constants import ActivityType, AuctionStatus, ExtensionTriggerMode, UserRole
from app.core.security import get_password_hash
from app.db.session import SessionLocal, engine
from app.models.activity import AuctionActivityLog
from app.models.bid import Bid
from app.models.extension import AuctionExtension
from app.models.rfq import RFQ
from app.models.user import User


def seed_database():
    db = SessionLocal()
    print("🌱 Starting British Auction RFQ demo data seeding...")

    # Clear existing demo data
    db.query(AuctionActivityLog).delete()
    db.query(AuctionExtension).delete()
    db.query(Bid).delete()
    db.query(RFQ).delete()
    db.query(User).delete()
    db.commit()

    # 1. Create Users
    password_hash = get_password_hash("password123")

    buyer = User(
        email="buyer@acme.corp",
        hashed_password=password_hash,
        full_name="Sarah Jenkins",
        company_name="Acme Global Procurement",
        role=UserRole.BUYER.value,
        supplier_code=None,
    )
    supplier1 = User(
        email="apex@logistics.com",
        hashed_password=password_hash,
        full_name="Marcus Vance",
        company_name="Apex Freight & Logistics",
        role=UserRole.SUPPLIER.value,
        supplier_code="APEX",
    )
    supplier2 = User(
        email="bluedart@freight.com",
        hashed_password=password_hash,
        full_name="Elena Rostova",
        company_name="BlueDart Express Global",
        role=UserRole.SUPPLIER.value,
        supplier_code="BLUEDART",
    )
    supplier3 = User(
        email="cargo@cargomaster.com",
        hashed_password=password_hash,
        full_name="Liam Chen",
        company_name="CargoMaster Solutions",
        role=UserRole.SUPPLIER.value,
        supplier_code="CARGOMASTER",
    )
    supplier4 = User(
        email="swift@trans.com",
        hashed_password=password_hash,
        full_name="Chloe Dubois",
        company_name="SwiftTrans Network",
        role=UserRole.SUPPLIER.value,
        supplier_code="SWIFT",
    )

    db.add_all([buyer, supplier1, supplier2, supplier3, supplier4])
    db.commit()
    for u in [buyer, supplier1, supplier2, supplier3, supplier4]:
        db.refresh(u)

    print(f"✅ Seeded 1 Buyer and 4 Suppliers")

    now = datetime.now(timezone.utc)

    # -------------------------------------------------------------
    # RFQ 1: Active Auction with extensions already triggered (Mode 1: BID_RECEIVED)
    # -------------------------------------------------------------
    rfq1_start = now - timedelta(hours=2)
    rfq1_init_close = now + timedelta(minutes=15)
    rfq1_forced_close = now + timedelta(minutes=45)
    rfq1_curr_close = now + timedelta(minutes=20)  # Extended once already by 5m

    rfq1 = RFQ(
        title="Automotive Parts Express Sea Freight",
        reference_id="RFQ-2026-001",
        description="High-priority 40ft HC containers automotive spares from Shanghai to Rotterdam port.",
        origin="Shanghai Port, China (CNSHA)",
        destination="Rotterdam Port, Netherlands (NLRTM)",
        cargo_details="5x 40ft High Cube Dry Containers (FCL) - Tier 1 Auto Components",
        pickup_date=date.today() + timedelta(days=14),
        british_auction_enabled=True,
        bid_start_time=rfq1_start,
        bid_close_time=rfq1_init_close,
        current_close_time=rfq1_curr_close,
        forced_close_time=rfq1_forced_close,
        trigger_window_minutes=10,
        extension_duration_minutes=5,
        extension_trigger_mode=ExtensionTriggerMode.BID_RECEIVED.value,
        status=AuctionStatus.ACTIVE.value,
        created_by_user_id=buyer.id,
    )
    db.add(rfq1)
    db.commit()
    db.refresh(rfq1)

    # Bids for RFQ 1
    # Initial bid by CargoMaster
    b1_1 = Bid(
        rfq_id=rfq1.id,
        supplier_id=supplier3.id,
        carrier_name="COSCO Shipping",
        freight_charges=Decimal("4200.00"),
        origin_charges=Decimal("450.00"),
        destination_charges=Decimal("350.00"),
        total_quote_amount=Decimal("5000.00"),
        transit_time_days=24,
        quote_validity_date=date.today() + timedelta(days=30),
        submitted_at=now - timedelta(minutes=40),
        rank_at_submission=1,
    )
    # Competitive bid by Apex Logistics
    b1_2 = Bid(
        rfq_id=rfq1.id,
        supplier_id=supplier1.id,
        carrier_name="Maersk Line",
        freight_charges=Decimal("3900.00"),
        origin_charges=Decimal("400.00"),
        destination_charges=Decimal("300.00"),
        total_quote_amount=Decimal("4600.00"),
        transit_time_days=22,
        quote_validity_date=date.today() + timedelta(days=30),
        submitted_at=now - timedelta(minutes=25),
        rank_at_submission=1,
    )
    # Late bid by BlueDart inside trigger window that extended the auction!
    b1_3 = Bid(
        rfq_id=rfq1.id,
        supplier_id=supplier2.id,
        carrier_name="Hapag-Lloyd",
        freight_charges=Decimal("3600.00"),
        origin_charges=Decimal("420.00"),
        destination_charges=Decimal("280.00"),
        total_quote_amount=Decimal("4300.00"),
        transit_time_days=20,
        quote_validity_date=date.today() + timedelta(days=30),
        submitted_at=now - timedelta(minutes=8),
        rank_at_submission=1,
    )
    db.add_all([b1_1, b1_2, b1_3])
    db.commit()
    for b in [b1_1, b1_2, b1_3]:
        db.refresh(b)

    rfq1.current_lowest_bid = Decimal("4300.00")
    rfq1.current_l1_supplier_id = supplier2.id
    db.add(rfq1)

    # Extension record for RFQ 1
    ext1 = AuctionExtension(
        rfq_id=rfq1.id,
        bid_id=b1_3.id,
        extended_at=b1_3.submitted_at,
        previous_close_time=rfq1_init_close,
        new_close_time=rfq1_curr_close,
        extension_minutes=5,
        trigger_mode=ExtensionTriggerMode.BID_RECEIVED.value,
        trigger_reason="Mode 1 [Bid Received]: Valid bid from BlueDart Express Global received inside last 10m. Auction extended by 5m.",
    )
    db.add(ext1)

    # Activity logs for RFQ 1
    log1_1 = AuctionActivityLog(
        rfq_id=rfq1.id,
        actor_id=buyer.id,
        activity_type=ActivityType.AUCTION_CREATED.value,
        headline=f"RFQ {rfq1.reference_id} created with British Auction enabled",
        details="Trigger: Bid Received in Last 10m, Extension: 5m, Forced Close: 45m buffer.",
        created_at=rfq1_start
    )
    log1_2 = AuctionActivityLog(
        rfq_id=rfq1.id,
        bid_id=b1_3.id,
        actor_id=supplier2.id,
        activity_type=ActivityType.EXTENSION_TRIGGERED.value,
        headline="Auction extended by 5 minutes",
        details="Bid submitted by BlueDart Express Global inside trigger window extended close time to " + rfq1_curr_close.isoformat(),
        created_at=b1_3.submitted_at
    )
    db.add_all([log1_1, log1_2])

    # -------------------------------------------------------------
    # RFQ 2: Active Auction with L1 Rank Change Trigger (Mode 3)
    # -------------------------------------------------------------
    rfq2 = RFQ(
        title="Pharmaceutical Cold Chain Air Cargo",
        reference_id="RFQ-2026-002",
        description="Temperature-controlled vaccines shipment (2°C - 8°C) Frankfurt to Singapore.",
        origin="Frankfurt Airport, Germany (FRA)",
        destination="Changi Airport, Singapore (SIN)",
        cargo_details="Envirotainer RAP e2 Unit (Refrigerated Pharma)",
        pickup_date=date.today() + timedelta(days=7),
        british_auction_enabled=True,
        bid_start_time=now - timedelta(hours=1),
        bid_close_time=now + timedelta(minutes=30),
        current_close_time=now + timedelta(minutes=30),
        forced_close_time=now + timedelta(hours=1),
        trigger_window_minutes=15,
        extension_duration_minutes=10,
        extension_trigger_mode=ExtensionTriggerMode.L1_RANK_CHANGE.value,
        status=AuctionStatus.ACTIVE.value,
        created_by_user_id=buyer.id,
    )
    db.add(rfq2)
    db.commit()
    db.refresh(rfq2)

    b2_1 = Bid(
        rfq_id=rfq2.id,
        supplier_id=supplier1.id,
        carrier_name="Lufthansa Cargo",
        freight_charges=Decimal("8500.00"),
        origin_charges=Decimal("600.00"),
        destination_charges=Decimal("450.00"),
        total_quote_amount=Decimal("9550.00"),
        transit_time_days=2,
        quote_validity_date=date.today() + timedelta(days=15),
        submitted_at=now - timedelta(minutes=20),
        rank_at_submission=1,
    )
    b2_2 = Bid(
        rfq_id=rfq2.id,
        supplier_id=supplier4.id,
        carrier_name="Singapore Airlines Cargo",
        freight_charges=Decimal("8900.00"),
        origin_charges=Decimal("550.00"),
        destination_charges=Decimal("400.00"),
        total_quote_amount=Decimal("9850.00"),
        transit_time_days=2,
        quote_validity_date=date.today() + timedelta(days=15),
        submitted_at=now - timedelta(minutes=10),
        rank_at_submission=2,
    )
    db.add_all([b2_1, b2_2])
    db.commit()
    rfq2.current_lowest_bid = Decimal("9550.00")
    rfq2.current_l1_supplier_id = supplier1.id
    db.add(rfq2)

    # -------------------------------------------------------------
    # RFQ 3: Closed Auction (Normal Close before Forced Close)
    # -------------------------------------------------------------
    rfq3 = RFQ(
        title="Industrial Heavy Machinery Overland Transport",
        reference_id="RFQ-2026-003",
        description="Specialized lowbed flatbed transport for oversized transformer units.",
        origin="Munich, Germany",
        destination="Milan, Italy",
        cargo_details="3x Flatbed trailers, 65 metric tons gross",
        pickup_date=date.today() - timedelta(days=2),
        british_auction_enabled=True,
        bid_start_time=now - timedelta(days=2),
        bid_close_time=now - timedelta(hours=5),
        current_close_time=now - timedelta(hours=5),
        forced_close_time=now - timedelta(hours=3),
        trigger_window_minutes=10,
        extension_duration_minutes=5,
        extension_trigger_mode=ExtensionTriggerMode.ANY_RANK_CHANGE.value,
        status=AuctionStatus.CLOSED.value,
        created_by_user_id=buyer.id,
        current_lowest_bid=Decimal("7200.00"),
        current_l1_supplier_id=supplier3.id,
    )
    db.add(rfq3)
    db.commit()
    db.refresh(rfq3)

    b3 = Bid(
        rfq_id=rfq3.id,
        supplier_id=supplier3.id,
        carrier_name="Kuehne+Nagel Road Logistics",
        freight_charges=Decimal("6200.00"),
        origin_charges=Decimal("500.00"),
        destination_charges=Decimal("500.00"),
        total_quote_amount=Decimal("7200.00"),
        transit_time_days=3,
        quote_validity_date=date.today() + timedelta(days=30),
        submitted_at=now - timedelta(days=1),
        rank_at_submission=1,
    )
    db.add(b3)

    # -------------------------------------------------------------
    # RFQ 4: Force-Closed Auction (Hit the Hard Cap)
    # -------------------------------------------------------------
    rfq4_close = now - timedelta(hours=2)
    rfq4 = RFQ(
        title="Cross-Border Electronics Fast Courier",
        reference_id="RFQ-2026-004",
        description="Daily consolidated pallet shipments of consumer electronics.",
        origin="Los Angeles, USA (LAX)",
        destination="Tokyo, Japan (NRT)",
        cargo_details="12 Pallets, Li-ion battery certified",
        pickup_date=date.today() - timedelta(days=1),
        british_auction_enabled=True,
        bid_start_time=now - timedelta(days=1),
        bid_close_time=rfq4_close - timedelta(minutes=20),
        current_close_time=rfq4_close,
        forced_close_time=rfq4_close,
        trigger_window_minutes=10,
        extension_duration_minutes=5,
        extension_trigger_mode=ExtensionTriggerMode.BID_RECEIVED.value,
        status=AuctionStatus.FORCE_CLOSED.value,
        created_by_user_id=buyer.id,
        current_lowest_bid=Decimal("11400.00"),
        current_l1_supplier_id=supplier4.id,
    )
    db.add(rfq4)
    db.commit()
    db.refresh(rfq4)

    b4 = Bid(
        rfq_id=rfq4.id,
        supplier_id=supplier4.id,
        carrier_name="FedEx International Priority",
        freight_charges=Decimal("10000.00"),
        origin_charges=Decimal("800.00"),
        destination_charges=Decimal("600.00"),
        total_quote_amount=Decimal("11400.00"),
        transit_time_days=3,
        quote_validity_date=date.today() + timedelta(days=15),
        submitted_at=rfq4_close - timedelta(minutes=2),
        rank_at_submission=1,
    )
    db.add(b4)

    ext4 = AuctionExtension(
        rfq_id=rfq4.id,
        bid_id=b4.id,
        extended_at=rfq4_close - timedelta(minutes=2),
        previous_close_time=rfq4_close - timedelta(minutes=5),
        new_close_time=rfq4_close,
        extension_minutes=5,
        trigger_mode=ExtensionTriggerMode.BID_RECEIVED.value,
        trigger_reason="Auction extended to FORCED CLOSE limit. Auction terminated by absolute deadline.",
    )
    db.add(ext4)

    db.commit()
    print("🎉 Demo database successfully seeded with 4 RFQs across all British Auction states!")
    db.close()


if __name__ == "__main__":
    seed_database()
