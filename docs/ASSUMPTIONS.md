# System Assumptions & Design Interpretations

This document records engineering assumptions made where the specification (`[Assignment] British Auction in RFQ System`) is open to interpretation, ensuring transparency, mathematical rigor, and alignment with enterprise procurement standards.

---

## 1. Monetary Values and Currency Handling
- **Assumption**: All quote components (`freight_charges`, `origin_charges`, `destination_charges`) and the computed total are stored as fixed-precision `NUMERIC(12, 2)` / Python `Decimal` values.
- **Rationale**: Floating-point representations (`float` / `double`) introduce binary precision errors (e.g., `0.1 + 0.2 != 0.3`) which are unacceptable in financial transactions.
- **Total Calculation**:
  $$\text{Total Quote Amount} = \text{freight\_charges} + \text{origin\_charges} + \text{destination\_charges}$$
- **Default Currency**: USD (`$`), displayed consistently across all frontend and API interfaces.

---

## 2. Supplier Bidding Model & Descending Price Competition
- **Assumption**: In a British reverse auction for freight procurement:
  1. A supplier can submit multiple bids over time as competition unfolds.
  2. Every accepted bid is stored as an immutable audit record in the database.
  3. A supplier's current standing in the ranking is evaluated based on their **best (lowest) valid bid**.
  4. **Strict Descending Rule**: A supplier cannot submit a new quote with a total price higher than their own previous lowest bid.
- **Rationale**: Prevents accidental or manipulative bid inflation while preserving complete bid history for compliance.

---

## 3. Deterministic Tie-Breaking
- **Assumption**: When two or more suppliers submit the exact same total quote amount:
  - The supplier whose bid was accepted earlier (lower `submitted_at` timestamp) takes the higher rank (e.g., L1 over L2).
- **Rationale**: In reverse auctions, "First to quote" rewards decisive pricing and eliminates ambiguity in rank assignment.

---

## 4. Trigger Window Evaluation (X Minutes)
- **Assumption**: The trigger window $X$ is evaluated against the **current effective bid close time** (`current_close_time`), not the initial bid close time.
- **Formula**:
  $$\text{Window Start} = \text{current\_close\_time} - X \text{ minutes}$$
  $$\text{In Trigger Window} \iff \text{Window Start} \le \text{bid\_time} < \text{current\_close\_time}$$
- **Rationale**: As the auction extends dynamically, subsequent bids must be evaluated against the newly established finish line.

---

## 5. Extension Calculation & Forced Close Hard Cap
- **Assumption**: When a valid bid meets the configured extension criteria:
  $$\text{new\_close\_time} = \min(\text{current\_close\_time} + Y \text{ minutes}, \text{forced\_close\_time})$$
- **Boundary Rules**:
  1. If `current_close_time == forced_close_time`, no further extensions occur.
  2. If `current_close_time + Y > forced_close_time`, the close time is extended only up to `forced_close_time`.
  3. Effective close time is monotonic (it can never move backward).

---

## 6. Extension Trigger Mode Semantics
1. **Mode 1 (`BID_RECEIVED`)**:
   - Any valid bid submitted within the final $X$ minutes extends the auction by $Y$ minutes (capped at forced close).
2. **Mode 2 (`ANY_RANK_CHANGE`)**:
   - The system compares the supplier ranking vector $[\text{Rank}_1, \dots, \text{Rank}_n]$ before the bid against the ranking vector after the bid.
   - If any supplier's rank ordinal changes (e.g., Supplier B moves from 2 to 1, or 3 to 2), an extension triggers.
   - If a bid arrives from an existing supplier that does not alter any supplier's rank, no extension occurs.
3. **Mode 3 (`L1_RANK_CHANGE`)**:
   - The system compares the L1 supplier ID before the bid vs after the bid.
   - An extension triggers **only** if the identity of the lowest bidder (L1) changes.
   - Bids that reshuffle lower positions (e.g. L2 vs L3) without dislodging L1 do not trigger an extension.

---

## 7. Auction Status Lifecycles
- `DRAFT` / `SCHEDULED`: Current time is before `bid_start_time`.
- `ACTIVE`: Current time is $\ge$ `bid_start_time` and $<$ `current_close_time` and $<$ `forced_close_time`.
- `CLOSED`: Current time is $\ge$ `current_close_time` where `current_close_time < forced_close_time`.
- `FORCE_CLOSED`: Current time is $\ge$ `forced_close_time` and the auction reached its forced deadline while active.

---

## 8. Authentication & Demo Personas
- **Assumption**: To provide realistic multi-stakeholder testing without requiring third-party OAuth or cloud accounts, the application provides:
  - Role-based authorization: `BUYER` and `SUPPLIER`.
  - Fast persona switching in the UI with seeded credentials.
  - Server-side JWT authentication ensuring bids cannot spoof supplier identities.
