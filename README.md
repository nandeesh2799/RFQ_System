# British Auction System for RFQ (Request for Quotation)

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-19-61DAFB.svg?logo=react&logoColor=black)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.8-3178C6.svg?logo=typescript&logoColor=white)](https://www.typescriptlang.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1.svg?logo=postgresql&logoColor=white)](https://www.postgresql.org)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-v4-38B2AC.svg?logo=tailwind-css&logoColor=white)](https://tailwindcss.com)
[![Playwright](https://img.shields.io/badge/Playwright-E2E-2EAD33.svg?logo=playwright&logoColor=white)](https://playwright.dev)
[![Pytest](https://img.shields.io/badge/Pytest-29_Passed-0A9EDC.svg?logo=pytest&logoColor=white)](https://pytest.org)

An enterprise-grade **British Reverse Auction Engine** integrated into a commercial freight logistics RFQ (Request for Quotation) platform. Built to the authoritative specification outlined in the assignment brief.

---

## 1. System Overview & British Auction Mechanics

In commercial procurement and freight logistics, reverse auctions allow pre-qualified suppliers (carriers) to compete by submitting descending quotations. 

A **British Auction** introduces dynamic time extensions to prevent "bid sniping" (waiting until the final seconds to submit a quote) while guaranteeing a hard finish:
- **Trigger Window ($X$ Minutes)**: The monitoring interval immediately preceding the current auction close time: $[T_{\text{close}} - X, T_{\text{close}}]$.
- **Extension Duration ($Y$ Minutes)**: The duration added to the deadline when competitive bidding conditions are satisfied.
- **Forced Bid Close Deadline ($T_{\text{forced\_close}}$)**: An absolute hard cap configured at RFQ creation ($T_{\text{forced\_close}} > T_{\text{initial\_close}}$). Extensions are strictly clamped:
  $$\text{New Close Time} = \min(T_{\text{current\_close}} + Y, T_{\text{forced\_close}})$$
  No extension can ever surpass the forced close deadline.

### Three Configurable Extension Trigger Modes
1. **Mode 1 (`BID_RECEIVED`)**: Extends by $+Y$ minutes whenever **any supplier** places a valid quotation within the final $X$ minutes.
2. **Mode 2 (`ANY_RANK_CHANGE`)**: Extends by $+Y$ minutes only when a quotation alters **any supplier's rank** (e.g., L3 overtakes L2, or L2 overtakes L1).
3. **Mode 3 (`L1_RANK_CHANGE`)**: Extends by $+Y$ minutes exclusively when the **lowest bidder (L1)** is dethroned. Submissions that do not take the L1 lead do not trigger extensions.

---

## 2. Key Architectural Features

- **ACID Row-Level Concurrency Control**: Quote submissions acquire PostgreSQL pessimistic row locks (`SELECT ... FOR UPDATE`) on the target RFQ record. This eliminates race conditions during concurrent bids, ensuring extension calculations and supplier ranks remain deterministic.
- **Pure Functional Domain Engine (`AuctionEngine`)**: Decoupled from I/O and databases. Calculations (quote summation, FIFO tie-breaking, boundary validation, and extension modes) are executed using an injectable `Clock` abstraction for microsecond time-travel testing.
- **Real-Time WebSockets**: Bids, deadline updates, and state transitions are broadcast to connected clients via `/ws/auctions/{rfq_id}` strictly after database transaction commit.
- **Zero-Friction Persona Switcher**: An interactive navbar dropdown allows reviewing engineers to alternate instantly between **Buyer** (`Acme Global Procurement`) and competing **Carriers** (`Apex Freight`, `BlueDart Express`, `CargoMaster`, `SwiftTrans Network`).

---

## 3. Tech Stack

- **Backend**: Python 3.12, FastAPI, SQLAlchemy 2 (async-ready 2.0 style), Alembic, Pydantic v2, PostgreSQL 16, Pytest.
- **Frontend**: React 19, TypeScript, Vite, Tailwind CSS v4, TanStack Query, React Hook Form, Zod, Lucide Icons.
- **End-to-End Testing**: Playwright (Headless Chromium).

---

## 4. Quick Start & Setup

### Prerequisites
- Docker & Docker Compose
- Python 3.12+
- Node.js 20+

### Step 1: Start PostgreSQL
```bash
docker compose up -d
```
*PostgreSQL will be running on `localhost:5432` with database `rfq_auction_db`.*

### Step 2: Initialize Backend & Seed Demo Data
```bash
cd backend

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Seed demo users and multi-lifecycle British Auctions
python scripts/seed_demo.py
```

### Step 3: Start the Backend Server
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
*FastAPI documentation will be accessible at [http://localhost:8000/docs](http://localhost:8000/docs).*

### Step 4: Start the Frontend Application
In a new terminal:
```bash
cd frontend

# Install dependencies
npm install

# Start Vite dev server
npm run dev
```
*Open [http://localhost:5173](http://localhost:5173) in your browser.*

---

## 5. Running Automated Tests

### Backend Unit, Adversarial & Concurrency Tests (29 Tests)
```bash
cd backend
source .venv/bin/activate
pytest -v
```

### Frontend Playwright End-to-End Tests (8 Tests)
```bash
cd frontend
npx playwright test
```

---

## 6. Demo Persona Accounts

| Persona Role | Company Name | Email | Carrier / Supplier Code |
| :--- | :--- | :--- | :--- |
| **Buyer** | Acme Global Procurement | `buyer@acme.corp` | *N/A (Procurement Team)* |
| **Carrier 1** | Apex Freight & Logistics | `apex@logistics.com` | `APEX` |
| **Carrier 2** | BlueDart Express Global | `bluedart@freight.com` | `BLUEDART` |
| **Carrier 3** | CargoMaster Solutions | `cargo@cargomaster.com` | `CARGOMASTER` |
| **Carrier 4** | SwiftTrans Network | `swift@trans.com` | `SWIFT` |

---

## 7. Documentation Index

- [High-Level Design & Mermaid Architecture (`docs/HLD.md`)](docs/HLD.md)
- [Database Schema & ER Diagram (`docs/DATABASE_SCHEMA.md`)](docs/DATABASE_SCHEMA.md)
- [Auction Rules & State Machine Spec (`docs/AUCTION_RULES.md`)](docs/AUCTION_RULES.md)
- [Engineering Assumptions (`docs/ASSUMPTIONS.md`)](docs/ASSUMPTIONS.md)
- [Comprehensive Test Report (`docs/TESTING.md`)](docs/TESTING.md)
- [Requirements Traceability Matrix (`docs/REQUIREMENTS_TRACEABILITY.md`)](docs/REQUIREMENTS_TRACEABILITY.md)
