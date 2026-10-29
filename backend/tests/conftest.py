import os
import sys
import pytest
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

# Ensure backend and root are on sys.path
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
BACKEND_DIR = os.path.join(ROOT_DIR, "backend")
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.db.base import Base
from app.db.session import engine, SessionLocal
from app.models.rfq import RFQ
from scripts.seed_demo import seed_database


@pytest.fixture(scope="session", autouse=True)
def setup_rfq_test_database():
    """Ensure database tables and dynamic demo fixtures exist for tests."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(RFQ).count() < 4:
            seed_database()
    finally:
        db.close()
    yield
