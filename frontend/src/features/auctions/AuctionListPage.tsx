import React, { useEffect, useState, useRef, useCallback } from "react";
import { Link } from "react-router-dom";
import { Search, PlusCircle, ArrowUpDown, Filter, Eye } from "lucide-react";
import { api } from "@/lib/api";
import type { RFQListItem } from "@/types";
import { StatusBadge, TriggerModeBadge } from "@/components/ui/Badge";

export const AuctionListPage: React.FC = () => {
  const [rfqs, setRfqs] = useState<RFQListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState("ALL");
  const [searchQuery, setSearchQuery] = useState("");
  const [sortField, setSortField] = useState<keyof RFQListItem>("created_at");
  const [sortAsc, setSortAsc] = useState(false);
  const activeReqRef = useRef(0);

  const loadAuctions = useCallback((filterToUse: string, queryToUse: string) => {
    const reqId = ++activeReqRef.current;
    setLoading(true);
    api.listRFQs(filterToUse, queryToUse)
      .then((data) => {
        if (reqId === activeReqRef.current) {
          setRfqs(data);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (reqId === activeReqRef.current) {
          setError(err.message);
          setLoading(false);
        }
      });
  }, []);

  useEffect(() => {
    loadAuctions(statusFilter, searchQuery);
  }, [statusFilter, loadAuctions]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    loadAuctions(statusFilter, searchQuery);
  };

  const handleSort = (field: keyof RFQListItem) => {
    if (sortField === field) {
      setSortAsc(!sortAsc);
    } else {
      setSortField(field);
      setSortAsc(true);
    }
  };

  const sortedRfqs = [...rfqs].sort((a, b) => {
    let aVal = a[sortField];
    let bVal = b[sortField];
    if (aVal === null || aVal === undefined) return 1;
    if (bVal === null || bVal === undefined) return -1;
    if (aVal < bVal) return sortAsc ? -1 : 1;
    if (aVal > bVal) return sortAsc ? 1 : -1;
    return 0;
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">British Auctions & RFQs</h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Overview of all active, completed, and force-closed reverse auctions.
          </p>
        </div>
        <Link
          to="/rfqs/new"
          className="inline-flex items-center space-x-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-lg shadow-xs transition"
        >
          <PlusCircle className="h-4 w-4" />
          <span>Create RFQ</span>
        </Link>
      </div>

      {/* Filter and Search Bar */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs flex flex-col md:flex-row gap-4 justify-between items-stretch md:items-center">
        {/* Status filter tabs */}
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="text-xs font-semibold text-slate-400 mr-2 flex items-center gap-1">
            <Filter className="h-3.5 w-3.5" /> Filter:
          </span>
          {["ALL", "ACTIVE", "CLOSED", "FORCE_CLOSED"].map((s) => (
            <button
              key={s}
              onClick={() => setStatusFilter(s)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                statusFilter === s
                  ? "bg-indigo-600 text-white shadow-xs"
                  : "bg-slate-100 text-slate-600 hover:bg-slate-200"
              }`}
            >
              {s === "ALL" ? "All Auctions" : s.replace("_", " ")}
            </button>
          ))}
        </div>

        {/* Search Input */}
        <form onSubmit={handleSearchSubmit} className="flex gap-2 w-full md:w-80">
          <div className="relative flex-1">
            <Search className="h-4 w-4 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Search reference, title, port..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:bg-white"
            />
          </div>
          <button
            type="submit"
            className="px-3 py-1.5 bg-slate-800 text-white text-xs font-semibold rounded-lg hover:bg-slate-900 transition"
          >
            Search
          </button>
        </form>
      </div>

      {/* Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
        {loading ? (
          <div className="py-20 flex flex-col items-center justify-center space-y-3">
            <div className="w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin" />
            <p className="text-xs text-slate-500 font-medium">Loading auctions...</p>
          </div>
        ) : error ? (
          <div className="py-16 text-center text-red-600 text-sm">{error}</div>
        ) : sortedRfqs.length === 0 ? (
          <div className="py-16 text-center text-slate-400 text-sm">
            No auctions matching your criteria.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50/75 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                  <th className="py-3 px-4 cursor-pointer" onClick={() => handleSort("reference_id")}>
                    <div className="flex items-center gap-1">RFQ Ref & Name <ArrowUpDown className="h-3 w-3" /></div>
                  </th>
                  <th className="py-3 px-4">Trigger Configuration</th>
                  <th className="py-3 px-4 cursor-pointer" onClick={() => handleSort("current_lowest_bid")}>
                    <div className="flex items-center gap-1">Current Lowest Bid <ArrowUpDown className="h-3 w-3" /></div>
                  </th>
                  <th className="py-3 px-4 cursor-pointer" onClick={() => handleSort("current_close_time")}>
                    <div className="flex items-center gap-1">Bid Close Time <ArrowUpDown className="h-3 w-3" /></div>
                  </th>
                  <th className="py-3 px-4">Forced Close</th>
                  <th className="py-3 px-4 cursor-pointer" onClick={() => handleSort("status")}>
                    <div className="flex items-center gap-1">Status <ArrowUpDown className="h-3 w-3" /></div>
                  </th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-xs">
                {sortedRfqs.map((rfq) => (
                  <tr key={rfq.id} className="hover:bg-slate-50/80 transition-colors">
                    {/* RFQ Name / ID */}
                    <td className="py-3.5 px-4">
                      <div className="font-semibold text-slate-900">{rfq.title}</div>
                      <div className="flex items-center gap-2 mt-0.5 text-slate-500 font-mono text-[11px]">
                        <span className="bg-slate-100 px-1.5 py-0.5 rounded text-slate-700 font-bold">{rfq.reference_id}</span>
                        <span>{rfq.origin} → {rfq.destination}</span>
                      </div>
                    </td>

                    {/* Trigger Configuration */}
                    <td className="py-3.5 px-4">
                      <TriggerModeBadge mode={rfq.extension_trigger_mode} />
                      <div className="text-[11px] text-slate-400 mt-1 font-mono">
                        Window: <strong>{rfq.trigger_window_minutes}m</strong> | Ext: <strong>+{rfq.extension_duration_minutes}m</strong>
                      </div>
                    </td>

                    {/* Current Lowest Bid */}
                    <td className="py-3.5 px-4">
                      {rfq.current_lowest_bid ? (
                        <div>
                          <span className="text-sm font-extrabold text-emerald-600 font-mono-num">
                            ${Number(rfq.current_lowest_bid).toLocaleString("en-US", { minimumFractionDigits: 2 })}
                          </span>
                          <div className="text-[10px] text-slate-400 mt-0.5">
                            {rfq.l1_supplier_name || "L1 Bid"} ({rfq.total_bids_count} bids)
                          </div>
                        </div>
                      ) : (
                        <span className="text-slate-400 italic">No quotes yet</span>
                      )}
                    </td>

                    {/* Current Bid Close Time */}
                    <td className="py-3.5 px-4 font-mono-num">
                      <div className="font-semibold text-slate-800">
                        {new Date(rfq.current_close_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </div>
                      <div className="text-[10px] text-slate-400">
                        {new Date(rfq.current_close_time).toLocaleDateString()}
                      </div>
                    </td>

                    {/* Forced Close Time */}
                    <td className="py-3.5 px-4 font-mono-num">
                      <div className="font-semibold text-purple-900">
                        {new Date(rfq.forced_close_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </div>
                      <div className="text-[10px] text-slate-400">
                        Hard Deadline
                      </div>
                    </td>

                    {/* Status */}
                    <td className="py-3.5 px-4">
                      <StatusBadge status={rfq.status} />
                    </td>

                    {/* Actions */}
                    <td className="py-3.5 px-4 text-right">
                      <Link
                        to={`/auctions/${rfq.id}`}
                        className="inline-flex items-center space-x-1.5 px-3 py-1.5 bg-slate-100 hover:bg-indigo-50 hover:text-indigo-700 text-slate-700 text-xs font-semibold rounded-lg transition"
                      >
                        <Eye className="h-3.5 w-3.5" />
                        <span>View Details</span>
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
