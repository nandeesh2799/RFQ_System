import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  TrendingDown,
  Activity,
  CheckCircle2,
  AlertOctagon,
  ArrowRight,
  Clock,
  Layers,
  PlusCircle
} from "lucide-react";
import { api } from "@/lib/api";
import type { DashboardStats } from "@/types";
import { StatusBadge } from "@/components/ui/Badge";

export const DashboardPage: React.FC = () => {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchStats = () => {
    api.getDashboardStats()
      .then((data) => {
        setStats(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  };

  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, 10000); // 10s auto refresh
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[500px]">
        <div className="flex flex-col items-center space-y-3">
          <div className="w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin" />
          <p className="text-sm text-slate-500 font-medium">Loading Procurement Dashboard...</p>
        </div>
      </div>
    );
  }

  if (error || !stats) {
    return (
      <div className="max-w-xl mx-auto mt-12 p-6 bg-red-50 border border-red-200 rounded-xl text-center">
        <p className="text-sm font-semibold text-red-800">Failed to load dashboard metrics</p>
        <p className="text-xs text-red-600 mt-1">{error}</p>
        <button
          onClick={fetchStats}
          className="mt-4 px-4 py-2 bg-red-600 text-white rounded-lg text-xs font-semibold hover:bg-red-700"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Procurement Dashboard</h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Real-time monitoring of British Auction RFQs, reverse-bidding dynamics, and extensions.
          </p>
        </div>
        <div className="flex gap-3">
          <Link
            to="/rfqs/new"
            className="inline-flex items-center space-x-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-lg shadow-xs transition"
          >
            <PlusCircle className="h-4 w-4" />
            <span>Create New RFQ</span>
          </Link>
        </div>
      </div>

      {/* KPI Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total RFQs */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Total RFQs</p>
            <p className="text-3xl font-extrabold text-slate-900 mt-1 font-mono-num">{stats.total_rfqs}</p>
          </div>
          <div className="h-12 w-12 rounded-lg bg-slate-100 flex items-center justify-center text-slate-600">
            <Layers className="h-6 w-6" />
          </div>
        </div>

        {/* Active Auctions */}
        <div className="bg-white p-5 rounded-xl border border-emerald-200 shadow-xs flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold text-emerald-600 uppercase tracking-wider">Active Auctions</p>
            <p className="text-3xl font-extrabold text-emerald-700 mt-1 font-mono-num">{stats.active_auctions}</p>
          </div>
          <div className="h-12 w-12 rounded-lg bg-emerald-50 flex items-center justify-center text-emerald-600">
            <Activity className="h-6 w-6 animate-pulse" />
          </div>
        </div>

        {/* Closed Auctions */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Normal Closed</p>
            <p className="text-3xl font-extrabold text-slate-800 mt-1 font-mono-num">{stats.closed_auctions}</p>
          </div>
          <div className="h-12 w-12 rounded-lg bg-slate-100 flex items-center justify-center text-slate-600">
            <CheckCircle2 className="h-6 w-6" />
          </div>
        </div>

        {/* Force Closed */}
        <div className="bg-white p-5 rounded-xl border border-purple-200 shadow-xs flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold text-purple-600 uppercase tracking-wider">Force-Closed</p>
            <p className="text-3xl font-extrabold text-purple-700 mt-1 font-mono-num">{stats.force_closed_auctions}</p>
          </div>
          <div className="h-12 w-12 rounded-lg bg-purple-50 flex items-center justify-center text-purple-600">
            <AlertOctagon className="h-6 w-6" />
          </div>
        </div>
      </div>

      {/* Grid: Active Lowest Bids & Upcoming Deadlines */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Active Auctions with Lowest Bids */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-xs p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <TrendingDown className="h-4 w-4 text-emerald-600" />
              Active Lowest Quotes (L1)
            </h2>
            <Link to="/auctions" className="text-xs text-indigo-600 font-semibold hover:underline flex items-center gap-1">
              View all <ArrowRight className="h-3 w-3" />
            </Link>
          </div>

          {stats.active_lowest_bids.length === 0 ? (
            <p className="text-sm text-slate-400 py-6 text-center">No active auctions right now.</p>
          ) : (
            <div className="divide-y divide-slate-100">
              {stats.active_lowest_bids.map((rfq) => (
                <div key={rfq.id} className="py-3 flex items-center justify-between hover:bg-slate-50/50 px-2 rounded-lg transition">
                  <div>
                    <Link to={`/auctions/${rfq.id}`} className="text-sm font-semibold text-slate-800 hover:text-indigo-600">
                      {rfq.title}
                    </Link>
                    <div className="flex items-center gap-2 mt-0.5 text-xs text-slate-500">
                      <span className="font-mono">{rfq.reference_id}</span>
                      <span>•</span>
                      <span>{rfq.origin} → {rfq.destination}</span>
                    </div>
                  </div>
                  <div className="text-right">
                    {rfq.current_lowest_bid ? (
                      <span className="text-base font-bold text-emerald-600 font-mono-num">
                        ${Number(rfq.current_lowest_bid).toLocaleString("en-US", { minimumFractionDigits: 2 })}
                      </span>
                    ) : (
                      <span className="text-xs text-slate-400 italic">No bids yet</span>
                    )}
                    <p className="text-[10px] text-slate-400 mt-0.5">
                      {rfq.l1_supplier_name ? `Leading: ${rfq.l1_supplier_name}` : "Awaiting quotes"}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Upcoming Auction Deadlines */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-xs p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <Clock className="h-4 w-4 text-amber-500" />
              Upcoming Auction Deadlines
            </h2>
            <Link to="/auctions" className="text-xs text-indigo-600 font-semibold hover:underline flex items-center gap-1">
              View table <ArrowRight className="h-3 w-3" />
            </Link>
          </div>

          {stats.upcoming_deadlines.length === 0 ? (
            <p className="text-sm text-slate-400 py-6 text-center">No impending deadlines.</p>
          ) : (
            <div className="divide-y divide-slate-100">
              {stats.upcoming_deadlines.map((rfq) => (
                <div key={rfq.id} className="py-3 flex items-center justify-between hover:bg-slate-50/50 px-2 rounded-lg transition">
                  <div>
                    <Link to={`/auctions/${rfq.id}`} className="text-sm font-semibold text-slate-800 hover:text-indigo-600">
                      {rfq.title}
                    </Link>
                    <p className="text-xs text-slate-500 mt-0.5">
                      Closing at: {new Date(rfq.current_close_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                    </p>
                  </div>
                  <div className="text-right">
                    <StatusBadge status={rfq.status} />
                    <p className="text-[10px] text-slate-400 mt-1 font-mono">
                      Window: {rfq.trigger_window_minutes}m | Ext: +{rfq.extension_duration_minutes}m
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Recent Auction Activity Timeline */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-xs p-5">
        <h2 className="text-base font-bold text-slate-900 mb-4 flex items-center gap-2">
          <Activity className="h-4 w-4 text-indigo-600" />
          Live Auction Activity Stream
        </h2>

        {stats.recent_activities.length === 0 ? (
          <p className="text-sm text-slate-400 py-6 text-center">No recent auction activities.</p>
        ) : (
          <div className="space-y-4">
            {stats.recent_activities.map((act) => (
              <div key={act.id} className="flex items-start space-x-3 text-sm pb-3 border-b border-slate-50 last:border-0 last:pb-0">
                <div className={`mt-0.5 h-2.5 w-2.5 rounded-full shrink-0 ${
                  act.activity_type === "EXTENSION_TRIGGERED" ? "bg-amber-500 animate-ping" :
                  act.activity_type === "BID_SUBMITTED" ? "bg-emerald-500" :
                  act.activity_type === "FORCED_CLOSE_TRIGGERED" ? "bg-purple-500" : "bg-indigo-500"
                }`} />
                <div className="flex-1">
                  <div className="flex justify-between items-baseline">
                    <span className="font-semibold text-slate-800">{act.headline}</span>
                    <span className="text-xs text-slate-400 font-mono">
                      {new Date(act.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                    </span>
                  </div>
                  {act.details && (
                    <p className="text-xs text-slate-500 mt-1">{act.details}</p>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
