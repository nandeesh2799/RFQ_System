# Requirements Traceability Matrix: British Auction in RFQ System

This matrix cross-references every functional and technical requirement specified in the PDF assignment document (`[Assignment] British Auction in RFQ System (1).pdf`) against the concrete implementation files and automated tests in the codebase.

| Req ID | Requirement Description | Implementation (Code / File) | Test Coverage |
| :--- | :--- | :--- | :--- |
| **REQ-01** | **British Auction Feature Toggle**<br>RFQ creation allows enabling British Auction mode. | `backend/app/models/rfq.py`<br>`frontend/src/features/auctions/CreateRFQPage.tsx` | `test_create_rfq_and_submit_bid_with_extension`<br>Playwright Spec 3 |
| **REQ-02** | **RFQ Identification**<br>Configures RFQ Name and unique Reference ID. | `RFQ.title`, `RFQ.reference_id`<br>`CreateRFQPage.tsx` | Playwright Spec 3 |
| **REQ-03** | **Bid Start Date & Time**<br>Defines when the auction officially opens for bidding. | `RFQ.bid_start_time`<br>`AuctionEngine.is_bid_eligible()` | `test_is_bid_eligible_boundaries` |
| **REQ-04** | **Initial Bid Close Date & Time**<br>Initial deadline before any extensions occur. | `RFQ.bid_close_time`<br>`RFQ.current_close_time` | `test_trigger_window_calculation` |
| **REQ-05** | **Forced Bid Close Date & Time**<br>Hard cutoff strictly greater than Initial Close Time. | `backend/app/schemas/rfq.py` (`model_validator`)<br>`CreateRFQPage.tsx` (Zod `.refine()`) | `test_forced_close_capping`<br>Playwright Spec 3 |
| **REQ-06** | **Pickup / Service Date**<br>Specifies cargo readiness date. | `RFQ.pickup_date`<br>`AuctionDetailPage.tsx` | Playwright Spec 4 |
| **REQ-07** | **Quote Breakdown Fields**<br>Carrier name, freight charges, origin charges, destination charges, transit time, quote validity. | `backend/app/models/bid.py`<br>`frontend/src/features/bids/BidSubmissionModal.tsx` | `test_quote_total_calculation`<br>Playwright Spec 5 |
| **REQ-08** | **Auto-Calculated Total Quote Amount**<br>$\text{Total} = \text{Freight} + \text{Origin} + \text{Destination}$. | `AuctionEngine.calculate_total_quote()`<br>`BidSubmissionModal.tsx` | `test_quote_total_calculation`<br>Playwright Spec 5 |
| **REQ-09** | **Trigger Window (X)**<br>Duration in minutes before deadline that activates extensions. | `RFQ.trigger_window_minutes`<br>`AuctionEngine.is_in_trigger_window()` | `test_trigger_window_calculation` |
| **REQ-10** | **Extension Duration (Y)**<br>Duration in minutes added when trigger fires. | `RFQ.extension_duration_minutes`<br>`AuctionEngine.evaluate_extension()` | `test_trigger_mode_1_bid_received` |
| **REQ-11** | **Extension Trigger Mode 1**<br>Extends if ANY valid bid is placed in last $X$ minutes. | `ExtensionTriggerMode.BID_RECEIVED`<br>`AuctionEngine.evaluate_extension()` | `test_trigger_mode_1_bid_received`<br>`test_create_rfq_and_submit_bid_with_extension` |
| **REQ-12** | **Extension Trigger Mode 2**<br>Extends if ANY supplier rank changes in last $X$ minutes. | `ExtensionTriggerMode.ANY_RANK_CHANGE`<br>`AuctionEngine.evaluate_extension()` | `test_trigger_mode_2_any_rank_change` |
| **REQ-13** | **Extension Trigger Mode 3**<br>Extends if lowest bidder (L1) rank changes in last $X$ minutes. | `ExtensionTriggerMode.L1_RANK_CHANGE`<br>`AuctionEngine.evaluate_extension()` | `test_trigger_mode_3_l1_rank_change`<br>Playwright Spec 3 |
| **REQ-14** | **Forced Close Capping**<br>Auction deadline is capped at $T_{\text{forced\_close}}$ and never exceeds it. | `AuctionEngine.evaluate_extension()`<br>`min(current_close + Y, forced_close)` | `test_forced_close_capping` |
| **REQ-15** | **Auction Status State Machine**<br>States: `Active`, `Closed`, and `Force Closed`. | `backend/app/core/constants.py`<br>`AuctionEngine.determine_status()`<br>`StatusBadge.tsx` | `test_auction_status_determination`<br>Playwright Spec 2 |
| **REQ-16** | **Auction Listing Screen**<br>Displays Name/ID, lowest bid, close time, forced close time, and status. | `frontend/src/features/auctions/AuctionListPage.tsx`<br>`GET /api/v1/rfqs` | `test_list_rfqs`<br>Playwright Spec 2 |
| **REQ-17** | **Auction Details Screen**<br>Displays bids sorted by price, rankings (L1, L2...), charge breakdown, $X/Y$ config, and activity log. | `frontend/src/features/auctions/AuctionDetailPage.tsx`<br>`GET /api/v1/rfqs/{id}` | Playwright Spec 4 & 5 |
| **REQ-18** | **Extension History & Audit Log**<br>Logs bid placements, extension times, and trigger reasons. | `backend/app/models/activity.py`<br>`backend/app/models/extension.py`<br>`AuctionActivityLog`, `AuctionExtension` | `test_create_rfq_and_submit_bid_with_extension`<br>Playwright Spec 4 |
