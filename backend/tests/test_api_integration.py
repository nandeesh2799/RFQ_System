from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from fastapi.testclient import TestClient
import pytest
from app.core.constants import ExtensionTriggerMode
from app.db.session import SessionLocal
from app.main import app
from app.models.rfq import RFQ
from app.models.user import User

client = TestClient(app)


def test_health_check():
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"


def test_list_rfqs():
    res = client.get("/api/v1/rfqs")
    assert res.status_code == 200
    rfqs = res.json()
    assert isinstance(rfqs, list)
    assert len(rfqs) >= 4


def test_dashboard_stats():
    res = client.get("/api/v1/dashboard/stats")
    assert res.status_code == 200
    stats = res.json()
    assert stats["total_rfqs"] >= 4
    assert stats["active_auctions"] >= 1


def test_create_rfq_and_submit_bid_with_extension():
    now = datetime.now(timezone.utc)
    # Create new RFQ with British Auction Mode 1 (BID_RECEIVED)
    payload = {
        "title": "Integration Test Air Freight",
        "reference_id": f"TEST-RFQ-{int(now.timestamp())}",
        "description": "Integration test for British Auction dynamic extension",
        "origin": "JFK New York",
        "destination": "LHR London",
        "cargo_details": "4 Pallets Cargo",
        "pickup_date": (date.today() + timedelta(days=5)).isoformat(),
        "british_auction_enabled": True,
        "bid_start_time": (now - timedelta(minutes=5)).isoformat(),
        "bid_close_time": (now + timedelta(minutes=5)).isoformat(),  # 5 min left -> inside 10m window!
        "forced_close_time": (now + timedelta(minutes=30)).isoformat(),
        "trigger_window_minutes": 10,
        "extension_duration_minutes": 5,
        "extension_trigger_mode": ExtensionTriggerMode.BID_RECEIVED.value
    }

    create_res = client.post(
        "/api/v1/rfqs",
        json=payload,
        headers={"X-Demo-User-Email": "buyer@acme.corp"}
    )
    assert create_res.status_code == 201, create_res.text
    created_rfq = create_res.json()
    rfq_id = created_rfq["id"]
    orig_close = datetime.fromisoformat(created_rfq["current_close_time"])

    # Submit a bid from Apex Logistics
    bid_payload = {
        "carrier_name": "British Airways Cargo",
        "freight_charges": 3000.00,
        "origin_charges": 300.00,
        "destination_charges": 200.00,
        "transit_time_days": 2,
        "quote_validity_date": (date.today() + timedelta(days=15)).isoformat(),
        "notes": "Direct flight express"
    }

    bid_res = client.post(
        f"/api/v1/rfqs/{rfq_id}/bids",
        json=bid_payload,
        headers={"X-Demo-User-Email": "apex@logistics.com"}
    )
    assert bid_res.status_code == 201, bid_res.text
    bid_data = bid_res.json()
    assert Decimal(str(bid_data["total_quote_amount"])) == Decimal("3500.00")

    # Fetch RFQ details and verify extension was applied!
    detail_res = client.get(f"/api/v1/rfqs/{rfq_id}")
    assert detail_res.status_code == 200
    detail = detail_res.json()

    new_close = datetime.fromisoformat(detail["current_close_time"])
    # Mode 1 inside 10m trigger window must have extended the close time by 5 minutes
    assert new_close > orig_close
    assert len(detail["extensions"]) == 1
    assert "Auction extended by 5m" in detail["extensions"][0]["trigger_reason"]
    assert detail["current_lowest_bid"] == "3500.00"
