import React, { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { X, Send, AlertCircle, Calculator } from "lucide-react";
import { api } from "@/lib/api";
import type { BidSubmissionForm } from "@/types";

const bidSchema = z.object({
  carrier_name: z.string().min(2, "Carrier name is required"),
  freight_charges: z.coerce.number().min(0, "Freight charges cannot be negative"),
  origin_charges: z.coerce.number().min(0, "Origin charges cannot be negative"),
  destination_charges: z.coerce.number().min(0, "Destination charges cannot be negative"),
  transit_time_days: z.coerce.number().int().positive("Transit time must be positive integer"),
  quote_validity_date: z.string().min(1, "Validity date is required"),
  notes: z.string().optional(),
});

interface BidModalProps {
  rfqId: number;
  isOpen: boolean;
  onClose: () => void;
  onBidSuccess: () => void;
  currentLowestBid?: number | null;
  supplierCurrentBest?: number | null;
}

export const BidSubmissionModal: React.FC<BidModalProps> = ({
  rfqId,
  isOpen,
  onClose,
  onBidSuccess,
  currentLowestBid,
  supplierCurrentBest,
}) => {
  const [submitting, setSubmitting] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);

  const validityDefault = new Date(Date.now() + 30 * 86400000).toISOString().slice(0, 10);

  const {
    register,
    handleSubmit,
    watch,
    reset,
    formState: { errors },
  } = useForm<BidSubmissionForm>({
    resolver: zodResolver(bidSchema) as any,
    defaultValues: {
      carrier_name: "Maersk Global Freight",
      freight_charges: 3500,
      origin_charges: 400,
      destination_charges: 300,
      transit_time_days: 18,
      quote_validity_date: validityDefault,
      notes: "Standard port-to-port maritime freight.",
    },
  });

  const freight = Number(watch("freight_charges")) || 0;
  const origin = Number(watch("origin_charges")) || 0;
  const destination = Number(watch("destination_charges")) || 0;
  const calculatedTotal = freight + origin + destination;

  if (!isOpen) return null;

  const onSubmit = async (data: BidSubmissionForm) => {
    setSubmitting(true);
    setServerError(null);
    try {
      await api.submitBid(rfqId, data);
      onBidSuccess();
      reset();
      onClose();
    } catch (err: any) {
      setServerError(err.message || "Failed to submit quote");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
      <div className="bg-white w-full max-w-lg rounded-2xl border border-slate-200 shadow-xl overflow-hidden animate-in fade-in zoom-in-95 duration-150">
        {/* Header */}
        <div className="px-6 py-4 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
          <div>
            <h3 className="text-base font-bold text-slate-900">Submit Quotation / Bid</h3>
            <p className="text-xs text-slate-500">Compete in British Auction by offering lower total charges.</p>
          </div>
          <button onClick={onClose} className="p-1 rounded-md text-slate-400 hover:text-slate-600">
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Alerts / Context */}
        <div className="px-6 pt-4 space-y-3">
          {currentLowestBid && (
            <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-lg text-xs text-emerald-900 flex items-center justify-between">
              <span>Current Auction Low (L1):</span>
              <strong className="font-mono text-sm">${Number(currentLowestBid).toFixed(2)}</strong>
            </div>
          )}

          {supplierCurrentBest && (
            <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-900 flex items-center justify-between">
              <span>Your Current Best Quote:</span>
              <strong className="font-mono text-sm">${Number(supplierCurrentBest).toFixed(2)}</strong>
            </div>
          )}

          {serverError && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-xs text-red-800 flex items-center gap-2">
              <AlertCircle className="h-4 w-4 text-red-600 shrink-0" />
              <span>{serverError}</span>
            </div>
          )}
        </div>

        <form onSubmit={handleSubmit(onSubmit)} className="p-6 space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
              Carrier Name *
            </label>
            <input
              type="text"
              {...register("carrier_name")}
              className="w-full text-xs px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:bg-white"
            />
            {errors.carrier_name && <p className="text-xs text-red-600 mt-1">{errors.carrier_name.message}</p>}
          </div>

          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="block text-[11px] font-semibold text-slate-700 uppercase tracking-wider mb-1">
                Freight ($) *
              </label>
              <input
                type="number"
                step="0.01"
                {...register("freight_charges")}
                className="w-full text-xs font-mono px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:bg-white"
              />
              {errors.freight_charges && <p className="text-[10px] text-red-600 mt-1">{errors.freight_charges.message}</p>}
            </div>

            <div>
              <label className="block text-[11px] font-semibold text-slate-700 uppercase tracking-wider mb-1">
                Origin ($) *
              </label>
              <input
                type="number"
                step="0.01"
                {...register("origin_charges")}
                className="w-full text-xs font-mono px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:bg-white"
              />
              {errors.origin_charges && <p className="text-[10px] text-red-600 mt-1">{errors.origin_charges.message}</p>}
            </div>

            <div>
              <label className="block text-[11px] font-semibold text-slate-700 uppercase tracking-wider mb-1">
                Destination ($) *
              </label>
              <input
                type="number"
                step="0.01"
                {...register("destination_charges")}
                className="w-full text-xs font-mono px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:bg-white"
              />
              {errors.destination_charges && <p className="text-[10px] text-red-600 mt-1">{errors.destination_charges.message}</p>}
            </div>
          </div>

          {/* Calculated Total Bar */}
          <div className="p-3.5 bg-slate-900 text-white rounded-xl flex items-center justify-between shadow-xs">
            <div className="flex items-center space-x-2">
              <Calculator className="h-4 w-4 text-indigo-400" />
              <span className="text-xs uppercase font-bold tracking-wider text-slate-300">Total Quote Amount:</span>
            </div>
            <div className="text-right">
              <span className="text-xl font-extrabold text-emerald-400 font-mono-num">
                ${calculatedTotal.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </span>
              <p className="text-[10px] text-slate-400">freight + origin + destination</p>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                Transit Time (Days) *
              </label>
              <input
                type="number"
                min="1"
                {...register("transit_time_days")}
                className="w-full text-xs font-mono px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:bg-white"
              />
              {errors.transit_time_days && <p className="text-xs text-red-600 mt-1">{errors.transit_time_days.message}</p>}
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                Quote Validity *
              </label>
              <input
                type="date"
                {...register("quote_validity_date")}
                className="w-full text-xs px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:bg-white"
              />
              {errors.quote_validity_date && <p className="text-xs text-red-600 mt-1">{errors.quote_validity_date.message}</p>}
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
              Notes (Optional)
            </label>
            <textarea
              rows={2}
              {...register("notes")}
              placeholder="Vessel routing, transshipment details, container equipment..."
              className="w-full text-xs px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:bg-white"
            />
          </div>

          <div className="flex justify-end space-x-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 border border-slate-200 text-slate-700 rounded-lg text-xs font-medium hover:bg-slate-50 transition"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="px-5 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-bold shadow-xs disabled:opacity-50 transition flex items-center gap-1.5"
            >
              <Send className="h-3.5 w-3.5" />
              <span>{submitting ? "Submitting..." : "Submit Quote"}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
