import React, { useEffect, useState, useRef, useCallback } from "react";
import { useParams, Link } from "react-router-dom";
import {
  ArrowLeft,
  Gavel,
  AlertTriangle,
  Send,
  TrendingDown,
  Package
} from "lucide-react";
import { api, getStoredDemoUser } from "@/lib/api";
import type { RFQDetail } from "@/types";
import { StatusBadge, TriggerModeBadge } from "@/components/ui/Badge";
import { Countdown } from "@/components/ui/Countdown";
import { BidSubmissionModal } from "@/features/bids/BidSubmissionModal";

export const AuctionDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [detail, setDetail] = useState<RFQDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<"bids" | "timeline" | "extensions">("bids");
  const [currentUserEmail, setCurrentUserEmail] = useState(getStoredDemoUser());
  const activeReqRef = useRef(0);

  const rfqId = Number(id);

  const fetchDetail = useCallback(() => {
    if (!rfqId) return;
    const reqId = ++activeReqRef.current;
    api.getRFQDetail(rfqId)
      .then((data) => {
        if (reqId === activeReqRef.current) {
          setDetail(data);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (reqId === activeReqRef.current) {
          setError(err.message);
          setLoading(false);
        }
      });
  }, [rfqId]);

  useEffect(() => {
    fetchDetail();
    // Connect WebSocket for live updates
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.host}/ws/auctions/${rfqId}`;
    let ws: WebSocket | null = null;
    try {
      ws = new WebSocket(wsUrl);
      ws.onmessage = () => {
        fetchDetail();
      };
    } catch {
      console.warn("WebSocket fallback to polling");
    }

    const interval = setInterval(fetchDetail, 5000);
    const handlePersonaChange = () => setCurrentUserEmail(getStoredDemoUser());
    window.addEventListener("persona_changed", handlePersonaChange);
    return () => {
      clearInterval(interval);
      window.removeEventListener("persona_changed", handlePersonaChange);
      if (ws) ws.close();
    };
  }, [rfqId, fetchDetail]);

  if (loading) {
    return (
      <div className="py-24 text-center">
        <div className="w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
        <p className="text-sm text-slate-500">Loading British Auction Details...</p>
      </div>
    );
  }

  if (error || !detail) {
    return (
      <div className="max-w-xl mx-auto my-12 p-6 bg-red-50 border border-red-200 rounded-xl text-center">
        <p className="text-sm font-semibold text-red-800">Failed to load auction details</p>
        <p className="text-xs text-red-600 mt-1">{error}</p>
        <Link to="/auctions" className="mt-4 inline-block px-4 py-2 bg-slate-800 text-white text-xs font-semibold rounded-lg">
          Back to Auctions
        </Link>
      </div>
    );
  }

  const isAuctionActive = detail.status === "ACTIVE";
  const isSupplier = currentUserEmail !== "buyer@acme.corp";
  const supplierRank = detail.rankings.find((r) => r.company_name.toLowerCase().includes(currentUserEmail.split("@")[0].toLowerCase()));

  return (
    <div className="space-y-6">
      {/* Top Breadcrumb & Action Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div className="flex items-center space-x-3">
          <Link to="/auctions" className="p-2 rounded-lg bg-white border border-slate-200 text-slate-500 hover:text-slate-800 transition">
            <ArrowLeft className="h-4 w-4" />
          </Link>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-mono text-xs font-bold px-2 py-0.5 rounded bg-slate-100 text-slate-800">
                {detail.reference_id}
              </span>
              <StatusBadge status={detail.status} />
              <TriggerModeBadge mode={detail.extension_trigger_mode} />
            </div>
            <h1 className="text-2xl font-bold text-slate-900 tracking-tight mt-1">{detail.title}</h1>
          </div>
        </div>

        {/* Action Button */}
        {isAuctionActive && isSupplier && (
          <button
            onClick={() => setModalOpen(true)}
            className="inline-flex items-center space-x-2 px-5 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-bold rounded-xl shadow-xs transition"
          >
            <Send className="h-4 w-4" />
            <span>Submit / Lower Quote</span>
          </button>
        )}
      </div>

      {/* Forced Close Alert Banner if reached */}
      {detail.has_reached_forced_close && (
        <div className="p-4 bg-purple-50 border border-purple-200 rounded-xl flex items-center gap-3 text-purple-900 text-sm">
          <AlertTriangle className="h-5 w-5 text-purple-600 shrink-0" />
          <div>
            <strong className="font-semibold">Auction Has Reached Forced Close Deadline ({new Date(detail.forced_close_time).toLocaleTimeString()}):</strong>
            <span className="text-purple-700 ml-1">No further time extensions can occur regardless of bidding activity.</span>
          </div>
        </div>
      )}

      {/* Main Grid: Info + Live Countdown */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: Cargo & Auction Rules */}
        <div className="lg:col-span-2 space-y-4">
          {/* Cargo Specs */}
          <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs space-y-3">
            <h2 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <Package className="h-4 w-4 text-indigo-600" />
              Shipment Specifications
            </h2>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-xs">
              <div className="bg-slate-50 p-3 rounded-lg">
                <span className="text-slate-400 font-semibold block text-[10px] uppercase">Routing</span>
                <span className="font-semibold text-slate-800 mt-0.5 block">{detail.origin} → {detail.destination}</span>
              </div>
              <div className="bg-slate-50 p-3 rounded-lg">
                <span className="text-slate-400 font-semibold block text-[10px] uppercase">Service / Pickup Date</span>
                <span className="font-semibold text-slate-800 mt-0.5 block">{detail.pickup_date}</span>
              </div>
              <div className="bg-slate-50 p-3 rounded-lg sm:col-span-1 col-span-2">
                <span className="text-slate-400 font-semibold block text-[10px] uppercase">Cargo Details</span>
                <span className="font-semibold text-slate-800 mt-0.5 block">{detail.cargo_details}</span>
              </div>
            </div>
            {detail.description && (
              <p className="text-xs text-slate-500 pt-1 leading-relaxed">{detail.description}</p>
            )}
          </div>

          {/* British Auction Config Breakdown */}
          <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs space-y-3">
            <h2 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <Gavel className="h-4 w-4 text-indigo-600" />
              British Auction Extension Mechanics
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
              <div className="border border-slate-200 p-3 rounded-lg">
                <span className="text-slate-400 font-semibold block text-[10px] uppercase">Trigger Window (X)</span>
                <span className="text-base font-bold text-indigo-700 font-mono-num">{detail.trigger_window_minutes} Minutes</span>
                <p className="text-[10px] text-slate-400 mt-1">Monitors bids before close</p>
              </div>
              <div className="border border-slate-200 p-3 rounded-lg">
                <span className="text-slate-400 font-semibold block text-[10px] uppercase">Extension Duration (Y)</span>
                <span className="text-base font-bold text-indigo-700 font-mono-num">+{detail.extension_duration_minutes} Minutes</span>
                <p className="text-[10px] text-slate-400 mt-1">Added per qualified trigger</p>
              </div>
              <div className="border border-slate-200 p-3 rounded-lg">
                <span className="text-slate-400 font-semibold block text-[10px] uppercase">Forced Close Deadline</span>
                <span className="text-base font-bold text-purple-800 font-mono-num">
                  {new Date(detail.forced_close_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </span>
                <p className="text-[10px] text-slate-400 mt-1">Absolute termination limit</p>
              </div>
            </div>
          </div>
        </div>

        {/* Right Col: Live Countdown & Leading Quote */}
        <div className="space-y-4">
          <Countdown
            targetDate={detail.current_close_time}
            forcedCloseDate={detail.forced_close_time}
            triggerWindowMinutes={detail.trigger_window_minutes}
          />

          {/* Current Leading L1 Quote */}
          <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs">
            <span className="text-xs uppercase font-semibold text-slate-400 flex items-center gap-1.5">
              <TrendingDown className="h-4 w-4 text-emerald-600" />
              Current Leading Quote (L1)
            </span>
            <div className="mt-2">
              {detail.current_lowest_bid ? (
                <div>
                  <span className="text-3xl font-extrabold text-emerald-600 font-mono-num">
                    ${Number(detail.current_lowest_bid).toLocaleString("en-US", { minimumFractionDigits: 2 })}
                  </span>
                  <p className="text-xs text-slate-500 mt-1">
                    Leader: <strong className="text-slate-800">{detail.rankings[0]?.company_name}</strong> ({detail.rankings[0]?.carrier_name})
                  </p>
                </div>
              ) : (
                <span className="text-sm text-slate-400 italic">No quotes submitted yet</span>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Tabs: Supplier Rankings / Bids / Activity Timeline / Extensions */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
        {/* Tab Headers */}
        <div className="flex border-b border-slate-200 bg-slate-50/50 px-4 text-xs font-semibold">
          <button
            onClick={() => setActiveTab("bids")}
            className={`py-3 px-4 border-b-2 transition ${
              activeTab === "bids"
                ? "border-indigo-600 text-indigo-700 bg-white font-bold"
                : "border-transparent text-slate-500 hover:text-slate-800"
            }`}
          >
            Supplier Rankings & Quotes ({detail.rankings.length})
          </button>
          <button
            onClick={() => setActiveTab("timeline")}
            className={`py-3 px-4 border-b-2 transition ${
              activeTab === "timeline"
                ? "border-indigo-600 text-indigo-700 bg-white font-bold"
                : "border-transparent text-slate-500 hover:text-slate-800"
            }`}
          >
            Activity Timeline ({detail.activities.length})
          </button>
          <button
            onClick={() => setActiveTab("extensions")}
            className={`py-3 px-4 border-b-2 transition ${
              activeTab === "extensions"
                ? "border-indigo-600 text-indigo-700 bg-white font-bold"
                : "border-transparent text-slate-500 hover:text-slate-800"
            }`}
          >
            Extension History ({detail.extensions.length})
          </button>
        </div>

        {/* Tab 1: Rankings & Quotes Table */}
        {activeTab === "bids" && (
          <div className="p-4">
            {detail.rankings.length === 0 ? (
              <div className="py-12 text-center text-slate-400 text-xs">
                No supplier quotes placed yet. Suppliers can submit bids using the action button above.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="border-b border-slate-200 text-slate-400 uppercase text-[10px] font-bold tracking-wider">
                      <th className="py-2.5 px-3">Rank</th>
                      <th className="py-2.5 px-3">Supplier & Carrier</th>
                      <th className="py-2.5 px-3 font-mono-num text-right">Freight ($)</th>
                      <th className="py-2.5 px-3 font-mono-num text-right">Origin ($)</th>
                      <th className="py-2.5 px-3 font-mono-num text-right">Dest ($)</th>
                      <th className="py-2.5 px-3 font-mono-num text-right">Total Quote ($)</th>
                      <th className="py-2.5 px-3 text-center">Transit</th>
                      <th className="py-2.5 px-3">Validity</th>
                      <th className="py-2.5 px-3">Submitted (UTC)</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {detail.rankings.map((r) => (
                      <tr key={r.bid_id} className={`hover:bg-slate-50 transition ${r.rank === 1 ? "bg-emerald-50/40" : ""}`}>
                        <td className="py-3 px-3">
                          <span className={`inline-flex items-center px-2 py-0.5 rounded font-mono font-bold text-xs ${
                            r.rank === 1 ? "bg-emerald-100 text-emerald-800" :
                            r.rank === 2 ? "bg-blue-100 text-blue-800" :
                            r.rank === 3 ? "bg-amber-100 text-amber-800" : "bg-slate-100 text-slate-700"
                          }`}>
                            L{r.rank}
                          </span>
                        </td>
                        <td className="py-3 px-3">
                          <span className="font-bold text-slate-900 block">{r.company_name}</span>
                          <span className="text-[11px] text-slate-500 font-mono">Carrier: {r.carrier_name}</span>
                        </td>
                        <td className="py-3 px-3 text-right font-mono-num">${Number(r.freight_charges).toFixed(2)}</td>
                        <td className="py-3 px-3 text-right font-mono-num">${Number(r.origin_charges).toFixed(2)}</td>
                        <td className="py-3 px-3 text-right font-mono-num">${Number(r.destination_charges).toFixed(2)}</td>
                        <td className="py-3 px-3 text-right font-mono-num">
                          <span className="font-extrabold text-slate-900 text-sm">
                            ${Number(r.total_quote_amount).toFixed(2)}
                          </span>
                        </td>
                        <td className="py-3 px-3 text-center font-mono-num">{r.transit_time_days}d</td>
                        <td className="py-3 px-3 text-slate-600">{r.quote_validity_date}</td>
                        <td className="py-3 px-3 text-slate-400 font-mono text-[11px]">
                          {new Date(r.submitted_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* Tab 2: Activity Timeline */}
        {activeTab === "timeline" && (
          <div className="p-5 space-y-4">
            {detail.activities.map((act) => (
              <div key={act.id} className="flex items-start space-x-3 text-xs border-b border-slate-100 pb-3 last:border-0 last:pb-0">
                <div className={`mt-0.5 h-2.5 w-2.5 rounded-full shrink-0 ${
                  act.activity_type === "EXTENSION_TRIGGERED" ? "bg-amber-500" :
                  act.activity_type === "BID_SUBMITTED" ? "bg-emerald-500" : "bg-indigo-500"
                }`} />
                <div className="flex-1">
                  <div className="flex justify-between items-baseline">
                    <span className="font-bold text-slate-800">{act.headline}</span>
                    <span className="text-slate-400 font-mono text-[11px]">
                      {new Date(act.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                    </span>
                  </div>
                  {act.details && <p className="text-slate-500 mt-1">{act.details}</p>}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Tab 3: Extensions History */}
        {activeTab === "extensions" && (
          <div className="p-5">
            {detail.extensions.length === 0 ? (
              <div className="py-8 text-center text-slate-400 text-xs">
                No extensions triggered yet. Extensions occur when bids meet the configured trigger rule inside the trigger window.
              </div>
            ) : (
              <div className="space-y-3">
                {detail.extensions.map((ext) => (
                  <div key={ext.id} className="p-3 bg-amber-50/60 border border-amber-200 rounded-lg text-xs space-y-1">
                    <div className="flex justify-between items-center font-bold text-amber-900">
                      <span>Extended by +{ext.extension_minutes} Minutes</span>
                      <span className="font-mono text-slate-500 text-[11px]">
                        Triggered at: {new Date(ext.extended_at).toLocaleTimeString()}
                      </span>
                    </div>
                    <div className="text-slate-600 font-mono text-[11px]">
                      Previous Close: {new Date(ext.previous_close_time).toLocaleTimeString()} → New Close: {new Date(ext.new_close_time).toLocaleTimeString()}
                    </div>
                    <p className="text-amber-800 font-medium pt-1">{ext.trigger_reason}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Quote Submission Modal */}
      <BidSubmissionModal
        rfqId={detail.id}
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        onBidSuccess={() => fetchDetail()}
        currentLowestBid={detail.current_lowest_bid}
        supplierCurrentBest={supplierRank ? Number(supplierRank.total_quote_amount) : null}
      />
    </div>
  );
};
