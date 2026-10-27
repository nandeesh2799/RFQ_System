export type UserRole = "BUYER" | "SUPPLIER" | "ADMIN";

export type AuctionStatus = "DRAFT" | "SCHEDULED" | "ACTIVE" | "CLOSED" | "FORCE_CLOSED";

export type ExtensionTriggerMode = "BID_RECEIVED" | "ANY_RANK_CHANGE" | "L1_RANK_CHANGE";

export interface User {
  id: number;
  email: string;
  full_name: string;
  company_name: string;
  role: UserRole;
  supplier_code?: string | null;
  is_active: boolean;
  created_at: string;
}

export interface RFQListItem {
  id: number;
  title: string;
  reference_id: string;
  origin: string;
  destination: string;
  pickup_date: string;
  british_auction_enabled: boolean;
  bid_start_time: string;
  bid_close_time: string;
  current_close_time: string;
  forced_close_time: string;
  trigger_window_minutes: number;
  extension_duration_minutes: number;
  extension_trigger_mode: ExtensionTriggerMode;
  status: AuctionStatus;
  current_lowest_bid?: number | null;
  total_bids_count: number;
  l1_supplier_name?: string | null;
  created_at: string;
}

export interface SupplierRankingItem {
  rank: number;
  supplier_id: number;
  supplier_name: string;
  company_name: string;
  carrier_name: string;
  total_quote_amount: number;
  freight_charges: number;
  origin_charges: number;
  destination_charges: number;
  transit_time_days: number;
  quote_validity_date: string;
  submitted_at: string;
  bid_id: number;
}

export interface Bid {
  id: number;
  rfq_id: number;
  supplier_id: number;
  carrier_name: string;
  freight_charges: number;
  origin_charges: number;
  destination_charges: number;
  total_quote_amount: number;
  transit_time_days: number;
  quote_validity_date: string;
  submitted_at: string;
  is_valid: boolean;
  rank_at_submission?: number | null;
  notes?: string | null;
  supplier?: User;
}

export interface AuctionExtension {
  id: number;
  rfq_id: number;
  bid_id?: number | null;
  extended_at: string;
  previous_close_time: string;
  new_close_time: string;
  extension_minutes: number;
  trigger_mode: ExtensionTriggerMode;
  trigger_reason: string;
}

export interface AuctionActivityLog {
  id: number;
  rfq_id: number;
  bid_id?: number | null;
  actor_id?: number | null;
  activity_type: string;
  headline: string;
  details?: string | null;
  extra_metadata?: Record<string, any> | null;
  created_at: string;
  actor?: User | null;
}

export interface RFQDetail {
  id: number;
  title: string;
  reference_id: string;
  description?: string | null;
  origin: string;
  destination: string;
  cargo_details: string;
  pickup_date: string;
  british_auction_enabled: boolean;
  bid_start_time: string;
  bid_close_time: string;
  current_close_time: string;
  forced_close_time: string;
  trigger_window_minutes: number;
  extension_duration_minutes: number;
  extension_trigger_mode: ExtensionTriggerMode;
  status: AuctionStatus;
  current_lowest_bid?: number | null;
  time_remaining_seconds: number;
  is_in_trigger_window: boolean;
  has_reached_forced_close: boolean;
  creator?: User | null;
  rankings: SupplierRankingItem[];
  bids: Bid[];
  extensions: AuctionExtension[];
  activities: AuctionActivityLog[];
  created_at: string;
  updated_at: string;
}

export interface DashboardStats {
  total_rfqs: number;
  active_auctions: number;
  closed_auctions: number;
  force_closed_auctions: number;
  recent_activities: AuctionActivityLog[];
  active_lowest_bids: RFQListItem[];
  upcoming_deadlines: RFQListItem[];
}

export interface BidSubmissionForm {
  carrier_name: string;
  freight_charges: number;
  origin_charges: number;
  destination_charges: number;
  transit_time_days: number;
  quote_validity_date: string;
  notes?: string;
}
