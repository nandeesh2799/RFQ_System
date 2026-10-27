# High-Level Design (HLD): British Auction RFQ System

## 1. Executive Architecture Summary

The British Auction RFQ System is an enterprise-grade reverse procurement platform designed for competitive freight contracting. In contrast to standard forward English auctions (where bids increment), a **British Reverse Auction** operates on descending pricing with dynamic deadline extensions triggered by late bidding activity, strictly constrained by a hard ceiling known as the **Forced Close Deadline**.

```mermaid
flowchart TD
    subgraph Frontend ["Frontend (React 19 + TypeScript + Vite + Tailwind CSS)"]
        UI_Dash[Procurement Dashboard]
        UI_List[Auction List & Filters]
        UI_Create[RFQ Creation Form]
        UI_Detail[Auction Detail & Live Timer]
        UI_Modal[Quote Submission Modal]
        UI_Persona[Demo Persona Switcher]
        WS_Client[WebSocket Real-Time Client]
    end

    subgraph API_Gateway ["FastAPI Application Layer (Port 8000)"]
        Router_Auth["/api/v1/auth (Demo Personas & JWT)"]
        Router_RFQ["/api/v1/rfqs (CRUD & Status)"]
        Router_Bid["/api/v1/rfqs/{id}/bids (Quote Submission)"]
        Router_Dash["/api/v1/dashboard (Procurement KPIs)"]
        WS_Manager["WebSocket ConnectionManager (/ws/auctions/{id})"]
    end

    subgraph Domain_Engine ["Core Domain Logic (AuctionEngine)"]
        Calc_Total["Total Quote Calculation: freight + origin + destination"]
        Calc_Ranks["Rankings & FIFO Tie-Breaking"]
        Calc_Window["Dynamic Trigger Window: [close - X, close]"]
        Eval_Ext["Extension Modes 1, 2, 3 Evaluation"]
        Cap_Forced["Hard Cap: min(close + Y, forced_close)"]
    end

    subgraph Data_Layer ["Data Tier (PostgreSQL 16 Engine)"]
        DB_Users[(users)]
        DB_RFQs[(rfqs - Row-level Locking)]
        DB_Bids[(bids)]
        DB_Ext[(auction_extensions)]
        DB_Logs[(auction_activity_logs)]
    end

    UI_Detail <-->|WebSocket Stream| WS_Manager
    UI_Dash & UI_List & UI_Create & UI_Modal -->|REST API Requests| API_Gateway
    Router_Bid -->|ACID Transaction with FOR UPDATE| DB_RFQs
    Router_Bid --> Domain_Engine
    Domain_Engine --> Router_Bid
    Router_Bid -->|Commit & Broadcast| WS_Manager
    WS_Manager -->|Push Events| WS_Client
```

---

## 2. Component Breakdown

### 2.1 Frontend Client
- **Tech Stack**: React 19, TypeScript, Vite, Tailwind CSS v4, TanStack Query, React Hook Form, Zod.
- **Key Modules**:
  - `DashboardPage`: Real-time operational overview with KPI metrics, lowest leading bids, upcoming deadlines, and activity logs.
  - `AuctionListPage`: Searchable, filterable table displaying status badges, trigger modes, leading bids, and close times.
  - `CreateRFQPage`: Logistics specification form with British Auction parameters ($X, Y$, Mode 1/2/3, Forced Close cap).
  - `AuctionDetailPage`: Full auction control room showing shipment specs, British Auction mechanics cards, SVG countdown timer, supplier rankings (L1, L2...), quote breakdowns, activity timeline, and extension history.
  - `BidSubmissionModal`: Real-time quote submission interface with automatic sum calculation (`freight + origin + destination`) and descending price validation.
  - `Navbar` & `PersonaSwitcher`: Allows instant persona toggling between the Buyer and competing Suppliers with zero logout overhead.

### 2.2 Backend Service Layer
- **Tech Stack**: FastAPI, Python 3.12, SQLAlchemy 2 (async-ready declarative), Alembic, Pydantic v2.
- **Key Services**:
  - `AuctionEngine`: Decoupled, pure functional domain engine evaluating boundaries, FIFO tie-breaking, dynamic trigger windows, trigger modes 1, 2, 3, and forced-close capping.
  - `BidService`: Transactional service managing database row locks (`with_for_update()`), ensuring race-free concurrency during bid evaluation.
  - `RFQService`: RFQ lifecycle state management, filter queries, detail composition, and procurement KPI aggregation.
  - `ConnectionManager`: WebSocket room manager broadcasting `BID_SUBMITTED`, `AUCTION_EXTENDED`, and `AUCTION_CLOSED` events.

---

## 3. Dynamic British Auction Lifecycle & Extension Sequence

```mermaid
sequenceDiagram
    autonumber
    actor Supplier as Competing Supplier (Carrier)
    participant UI as Frontend Auction Detail
    participant API as FastAPI Bid API
    participant Lock as PostgreSQL RFQ Row Lock
    participant Engine as AuctionEngine
    participant DB as Database (Postgres)
    participant WS as WebSocket Manager
    actor Buyer as Buyer & Other Carriers

    Supplier->>UI: Submit quote (Freight + Origin + Dest)
    UI->>API: POST /api/v1/rfqs/{id}/bids
    Note over API,Lock: Begin Transaction
    API->>Lock: SELECT * FROM rfqs WHERE id = :id FOR UPDATE
    API->>Engine: is_bid_eligible(bid_time, start, close, forced)
    Engine-->>API: Eligible (True)
    API->>Engine: calculate_total_quote(freight, origin, dest)
    API->>Engine: calculate_rankings(current_bids)
    API->>Engine: evaluate_extension(mode, bid_time, current_close, forced_close, X, Y, ...)
    alt Trigger Condition Met & Not Reached Forced Close
        Engine-->>API: Extension Triggered (new_close = min(current_close + Y, forced_close))
        API->>DB: INSERT INTO auction_extensions
        API->>DB: UPDATE rfqs SET current_close_time = :new_close
        API->>DB: INSERT INTO auction_activity_logs (EXTENSION_TRIGGERED)
    else Condition Not Met or Already at Forced Close
        Engine-->>API: No Extension
    end
    API->>DB: INSERT INTO bids
    API->>DB: INSERT INTO auction_activity_logs (BID_SUBMITTED)
    Note over API,Lock: Commit Transaction & Release Lock
    API->>WS: broadcast_to_room(rfq_id, event)
    WS-->>UI: Real-Time Event (Push update)
    WS-->>Buyer: Real-Time Event (Update countdown & ranking table)
    API-->>UI: HTTP 201 Created (Bid & Ranking Response)
```

---

## 4. Trigger Mode State Logic

| Mode | Trigger Name | Condition for +Y Extension | Evaluation Window |
| :--- | :--- | :--- | :--- |
| **Mode 1** | **Bid Received** | Any valid bid submitted | $[T_{\text{close}} - X, T_{\text{close}}]$ |
| **Mode 2** | **Any Rank Change** | Any supplier moves up or down in rankings | $[T_{\text{close}} - X, T_{\text{close}}]$ |
| **Mode 3** | **L1 Rank Change** | The leading bidder (Rank 1) is dethroned | $[T_{\text{close}} - X, T_{\text{close}}]$ |

### Forced Close Cap Formula
$$\text{New Close Time} = \min(T_{\text{current\_close}} + Y, T_{\text{forced\_close}})$$
If $T_{\text{current\_close}} \ge T_{\text{forced\_close}}$, no further extension occurs, and the status permanently shifts to `FORCE_CLOSED`.
