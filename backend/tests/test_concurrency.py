from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from fastapi.testclient import TestClient
import pytest
from app.core.constants import ExtensionTriggerMode
from app.main import app

client = TestClient(app)


def test_concurrent_bids_from_multiple_suppliers():
    """
    Submits simultaneous bids from 4 distinct suppliers to test row-level locking
    and race-condition prevention under concurrent load.
    """
    now = datetime.now(timezone.utc)
    rfq_payload = {
        "title": "Concurrent Stress Testing RFQ",
        "reference_id": f"CONCUR-{int(now.timestamp())}",
        "description": "High-concurrency British Auction stress test",
        "origin": "Port of Singapore",
        "destination": "Port of Antwerp",
        "cargo_details": "10x 40ft Containers",
        "pickup_date": (date.today() + timedelta(days=10)).isoformat(),
        "british_auction_enabled": True,
        "bid_start_time": (now - timedelta(minutes=5)).isoformat(),
        "bid_close_time": (now + timedelta(minutes=8)).isoformat(),  # Inside 10m trigger window
        "forced_close_time": (now + timedelta(minutes=60)).isoformat(),
        "trigger_window_minutes": 10,
        "extension_duration_minutes": 5,
        "extension_trigger_mode": ExtensionTriggerMode.BID_RECEIVED.value,
    }

    create_res = client.post(
        "/api/v1/rfqs",
        json=rfq_payload,
        headers={"X-Demo-User-Email": "buyer@acme.corp"}
    )
    assert create_res.status_code == 201
    rfq_id = create_res.json()["id"]

    carriers = [
        {"email": "apex@logistics.com", "name": "Apex", "freight": 4000.00},
        {"email": "bluedart@freight.com", "name": "BlueDart", "freight": 3800.00},
        {"email": "cargo@cargomaster.com", "name": "CargoMaster", "freight": 3600.00},
        {"email": "swift@trans.com", "name": "SwiftTrans", "freight": 3400.00},
    ]

    def post_bid(carrier_info):
        # Create a fresh client instance per thread for thread safety
        thread_client = TestClient(app)
        bid_body = {
            "carrier_name": f"{carrier_info['name']} Express",
            "freight_charges": carrier_info["freight"],
            "origin_charges": 200.00,
            "destination_charges": 100.00,
            "transit_time_days": 14,
            "quote_validity_date": (date.today() + timedelta(days=30)).isoformat(),
            "notes": "Concurrent test submission"
        }
        res = thread_client.post(
            f"/api/v1/rfqs/{rfq_id}/bids",
            json=bid_body,
            headers={"X-Demo-User-Email": carrier_info["email"]}
        )
        return res.status_code, res.json()

    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(post_bid, carriers))

    # All 4 simultaneous submissions must succeed (status 201)
    status_codes = [r[0] for r in results]
    assert status_codes == [201, 201, 201, 201]

    # Fetch RFQ details and verify all 4 bids are accounted for with proper rankings
    detail_res = client.get(f"/api/v1/rfqs/{rfq_id}")
    assert detail_res.status_code == 200
    detail = detail_res.json()

    assert len(detail["rankings"]) == 4
    # Lowest total quote is SwiftTrans (3400 + 200 + 100 = 3700.00) -> L1
    assert detail["rankings"][0]["rank"] == 1
    assert detail["rankings"][0]["carrier_name"] == "SwiftTrans Express"
    assert Decimal(str(detail["current_lowest_bid"])) == Decimal("3700.00")


def test_descending_price_rejection():
    """
    Verifies that a supplier cannot submit a bid higher than their own previous best bid.
    """
    now = datetime.now(timezone.utc)
    rfq_payload = {
        "title": "Descending Price Test RFQ",
        "reference_id": f"DESC-{int(now.timestamp())}",
        "origin": "Hamburg",
        "destination": "New York",
        "cargo_details": "1 Container",
        "pickup_date": (date.today() + timedelta(days=5)).isoformat(),
        "british_auction_enabled": True,
        "bid_start_time": (now - timedelta(minutes=5)).isoformat(),
        "bid_close_time": (now + timedelta(minutes=30)).isoformat(),
        "forced_close_time": (now + timedelta(minutes=60)).isoformat(),
        "trigger_window_minutes": 10,
        "extension_duration_minutes": 5,
        "extension_trigger_mode": ExtensionTriggerMode.BID_RECEIVED.value,
    }
    create_res = client.post("/api/v1/rfqs", json=rfq_payload, headers={"X-Demo-User-Email": "buyer@acme.corp"})
    assert create_res.status_code == 201
    rfq_id = create_res.json()["id"]

    # 1. Apex submits quote of $3,500.00 (3000 freight + 300 origin + 200 dest)
    bid1 = {
        "carrier_name": "Apex Line",
        "freight_charges": 3000.00,
        "origin_charges": 300.00,
        "destination_charges": 200.00,
        "transit_time_days": 10,
        "quote_validity_date": (date.today() + timedelta(days=20)).isoformat(),
    }
    res1 = client.post(f"/api/v1/rfqs/{rfq_id}/bids", json=bid1, headers={"X-Demo-User-Email": "apex@logistics.com"})
    assert res1.status_code == 201

    # 2. Apex attempts to submit higher quote of $3,800.00 (3300 freight + 300 origin + 200 dest)
    higher_bid = {
        "carrier_name": "Apex Line",
        "freight_charges": 3300.00,
        "origin_charges": 300.00,
        "destination_charges": 200.00,
        "transit_time_days": 10,
        "quote_validity_date": (date.today() + timedelta(days=20)).isoformat(),
    }
    res2 = client.post(f"/api/v1/rfqs/{rfq_id}/bids", json=higher_bid, headers={"X-Demo-User-Email": "apex@logistics.com"})
    assert res2.status_code == 400
    assert "Descending price rule" in res2.json()["detail"]

    # 3. Apex submits lower quote of $3,200.00 -> Accepted!
    lower_bid = {
        "carrier_name": "Apex Line",
        "freight_charges": 2700.00,
        "origin_charges": 300.00,
        "destination_charges": 200.00,
        "transit_time_days": 10,
        "quote_validity_date": (date.today() + timedelta(days=20)).isoformat(),
    }
    res3 = client.post(f"/api/v1/rfqs/{rfq_id}/bids", json=lower_bid, headers={"X-Demo-User-Email": "apex@logistics.com"})
    assert res3.status_code == 201
