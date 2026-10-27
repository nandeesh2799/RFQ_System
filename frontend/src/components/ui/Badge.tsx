import React from "react";
import type { AuctionStatus, ExtensionTriggerMode } from "@/types";

interface StatusBadgeProps {
  status: AuctionStatus | string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status }) => {
  switch (status) {
    case "ACTIVE":
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-600" />
          Active
        </span>
      );
    case "FORCE_CLOSED":
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-purple-50 text-purple-700 border border-purple-200">
          <span className="h-1.5 w-1.5 rounded-full bg-purple-600" />
          Force Closed
        </span>
      );
    case "CLOSED":
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-100 text-slate-700 border border-slate-300">
          <span className="h-1.5 w-1.5 rounded-full bg-slate-500" />
          Closed
        </span>
      );
    case "SCHEDULED":
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-sky-50 text-sky-700 border border-sky-200">
          <span className="h-1.5 w-1.5 rounded-full bg-sky-600" />
          Scheduled
        </span>
      );
    default:
      return (
        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-100 text-slate-600 border border-slate-200">
          {status}
        </span>
      );
  }
};

interface TriggerModeBadgeProps {
  mode: ExtensionTriggerMode | string;
}

export const TriggerModeBadge: React.FC<TriggerModeBadgeProps> = ({ mode }) => {
  switch (mode) {
    case "BID_RECEIVED":
      return (
        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-slate-100 text-slate-700 border border-slate-200" title="Extends if any bid is placed in trigger window">
          Mode 1: Any Bid Received
        </span>
      );
    case "ANY_RANK_CHANGE":
      return (
        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-indigo-50 text-indigo-700 border border-indigo-200" title="Extends if any supplier rank changes in trigger window">
          Mode 2: Any Rank Change
        </span>
      );
    case "L1_RANK_CHANGE":
      return (
        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-amber-50 text-amber-800 border border-amber-200" title="Extends only if lowest bidder (L1) changes in trigger window">
          Mode 3: L1 Rank Change
        </span>
      );
    default:
      return <span className="text-xs text-slate-600">{mode}</span>;
  }
};
