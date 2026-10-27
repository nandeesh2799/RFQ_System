import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { Gavel, AlertCircle, ArrowLeft } from "lucide-react";
import { api } from "@/lib/api";

const createRFQSchema = z.object({
  title: z.string().min(3, "RFQ Title must be at least 3 characters"),
  reference_id: z.string().min(3, "Reference ID must be at least 3 characters"),
  description: z.string().optional(),
  origin: z.string().min(2, "Origin location is required"),
  destination: z.string().min(2, "Destination location is required"),
  cargo_details: z.string().min(2, "Cargo details are required"),
  pickup_date: z.string().min(1, "Pickup date is required"),
  british_auction_enabled: z.boolean(),
  bid_start_time: z.string().min(1, "Bid start time is required"),
  bid_close_time: z.string().min(1, "Bid close time is required"),
  forced_close_time: z.string().min(1, "Forced close time is required"),
  trigger_window_minutes: z.coerce.number().int().positive("Trigger window X must be a positive integer"),
  extension_duration_minutes: z.coerce.number().int().positive("Extension duration Y must be a positive integer"),
  extension_trigger_mode: z.enum(["BID_RECEIVED", "ANY_RANK_CHANGE", "L1_RANK_CHANGE"]),
}).refine((data) => new Date(data.bid_start_time) < new Date(data.bid_close_time), {
  message: "Start time must be earlier than initial bid close time",
  path: ["bid_close_time"],
}).refine((data) => new Date(data.forced_close_time) > new Date(data.bid_close_time), {
  message: "Forced bid close time must be strictly later than initial bid close time",
  path: ["forced_close_time"],
});

type FormData = z.infer<typeof createRFQSchema>;

export const CreateRFQPage: React.FC = () => {
  const navigate = useNavigate();
  const [serverError, setServerError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // Format Date for HTML5 datetime-local input (YYYY-MM-DDTHH:mm) in local timezone
  const toLocalISOString = (d: Date) => {
    const pad = (n: number) => String(n).padStart(2, "0");
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
  };

  // Compute sensible default dates:
  const now = new Date();
  const startDefault = toLocalISOString(new Date(now.getTime() - 5 * 60000));
  const closeDefault = toLocalISOString(new Date(now.getTime() + 60 * 60000));
  const forcedDefault = toLocalISOString(new Date(now.getTime() + 120 * 60000));
  const pickupDefault = new Date(now.getTime() + 7 * 86400000).toISOString().slice(0, 10);
  const randomRef = `RFQ-${now.getFullYear()}-${Math.floor(100 + Math.random() * 900)}`;

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors },
  } = useForm<FormData>({
    resolver: zodResolver(createRFQSchema) as any,
    defaultValues: {
      title: "Commercial Freight Transportation Contract",
      reference_id: randomRef,
      description: "Standard FCL container shipment under British Auction competitive reverse bidding.",
      origin: "Port of Los Angeles, USA",
      destination: "Hamburg Port, Germany",
      cargo_details: "4x 40ft High-Cube Standard Dry Containers",
      pickup_date: pickupDefault,
      british_auction_enabled: true,
      bid_start_time: startDefault,
      bid_close_time: closeDefault,
      forced_close_time: forcedDefault,
      trigger_window_minutes: 10,
      extension_duration_minutes: 5,
      extension_trigger_mode: "BID_RECEIVED",
    },
  });

  const selectedTriggerMode = watch("extension_trigger_mode");

  const onSubmit = async (data: FormData) => {
    setSubmitting(true);
    setServerError(null);
    try {
      const payload = {
        ...data,
        bid_start_time: new Date(data.bid_start_time).toISOString(),
        bid_close_time: new Date(data.bid_close_time).toISOString(),
        forced_close_time: new Date(data.forced_close_time).toISOString(),
      };
      const created = await api.createRFQ(payload);
      navigate(`/auctions/${created.id}`);
    } catch (err: any) {
      setServerError(err.message || "Failed to create RFQ");
      setSubmitting(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center space-x-3">
        <button
          onClick={() => navigate(-1)}
          className="p-2 rounded-lg bg-white border border-slate-200 text-slate-500 hover:text-slate-800 transition"
        >
          <ArrowLeft className="h-4 w-4" />
        </button>
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Create New RFQ Auction</h1>
          <p className="text-sm text-slate-500">Configure logistics requirements and British Auction parameters.</p>
        </div>
      </div>

      {serverError && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-xl flex items-center space-x-3 text-red-800 text-sm">
          <AlertCircle className="h-5 w-5 text-red-600 shrink-0" />
          <span>{serverError}</span>
        </div>
      )}

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        {/* Section 1: RFQ & Cargo Details */}
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-xs space-y-4">
          <h2 className="text-base font-bold text-slate-900 pb-2 border-b border-slate-100 flex items-center gap-2">
            1. RFQ & Cargo Specifications
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                RFQ Name / Title *
              </label>
              <input
                type="text"
                {...register("title")}
                className="w-full text-sm px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:bg-white"
              />
              {errors.title && <p className="text-xs text-red-600 mt-1">{errors.title.message}</p>}
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                Unique Reference ID *
              </label>
              <input
                type="text"
                {...register("reference_id")}
                className="w-full text-sm font-mono px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:bg-white"
              />
              {errors.reference_id && <p className="text-xs text-red-600 mt-1">{errors.reference_id.message}</p>}
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                Origin *
              </label>
              <input
                type="text"
                {...register("origin")}
                className="w-full text-sm px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:bg-white"
              />
              {errors.origin && <p className="text-xs text-red-600 mt-1">{errors.origin.message}</p>}
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                Destination *
              </label>
              <input
                type="text"
                {...register("destination")}
                className="w-full text-sm px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:bg-white"
              />
              {errors.destination && <p className="text-xs text-red-600 mt-1">{errors.destination.message}</p>}
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                Cargo / Shipment Details *
              </label>
              <input
                type="text"
                {...register("cargo_details")}
                className="w-full text-sm px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:bg-white"
              />
              {errors.cargo_details && <p className="text-xs text-red-600 mt-1">{errors.cargo_details.message}</p>}
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                Pickup / Service Date *
              </label>
              <input
                type="date"
                {...register("pickup_date")}
                className="w-full text-sm px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:bg-white"
              />
              {errors.pickup_date && <p className="text-xs text-red-600 mt-1">{errors.pickup_date.message}</p>}
            </div>
          </div>
        </div>

        {/* Section 2: British Auction Rules & Timing */}
        <div className="bg-white p-6 rounded-xl border border-indigo-200 shadow-xs space-y-5">
          <div className="flex items-center justify-between pb-2 border-b border-slate-100">
            <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <Gavel className="h-4 w-4 text-indigo-600" />
              2. British Auction Parameters & Forced Close Rules
            </h2>
            <label className="flex items-center space-x-2 cursor-pointer">
              <input
                type="checkbox"
                {...register("british_auction_enabled")}
                className="h-4 w-4 text-indigo-600 rounded border-slate-300 focus:ring-indigo-500"
              />
              <span className="text-xs font-semibold text-slate-700">British Auction Enabled</span>
            </label>
          </div>

          {/* Timestamps */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                Bid Start Date & Time *
              </label>
              <input
                type="datetime-local"
                {...register("bid_start_time")}
                className="w-full text-xs font-mono px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:bg-white"
              />
              {errors.bid_start_time && <p className="text-xs text-red-600 mt-1">{errors.bid_start_time.message}</p>}
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                Initial Bid Close Date & Time *
              </label>
              <input
                type="datetime-local"
                {...register("bid_close_time")}
                className="w-full text-xs font-mono px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:bg-white"
              />
              {errors.bid_close_time && <p className="text-xs text-red-600 mt-1">{errors.bid_close_time.message}</p>}
            </div>

            <div>
              <label className="block text-xs font-semibold text-purple-900 uppercase tracking-wider mb-1">
                Forced Close Deadline (Hard Cap) *
              </label>
              <input
                type="datetime-local"
                {...register("forced_close_time")}
                className="w-full text-xs font-mono px-3 py-2 bg-purple-50/50 border border-purple-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 focus:bg-white"
              />
              <p className="text-[10px] text-slate-400 mt-1">Rule: Must be strictly later than Initial Bid Close Time.</p>
              {errors.forced_close_time && <p className="text-xs text-red-600 mt-1">{errors.forced_close_time.message}</p>}
            </div>
          </div>

          {/* Trigger Window X and Extension Duration Y */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                Trigger Window X (Minutes) *
              </label>
              <input
                type="number"
                min="1"
                {...register("trigger_window_minutes")}
                className="w-full text-sm font-mono px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:bg-white"
              />
              <p className="text-[10px] text-slate-400 mt-1">Monitors bids in the final X minutes before current close time.</p>
              {errors.trigger_window_minutes && <p className="text-xs text-red-600 mt-1">{errors.trigger_window_minutes.message}</p>}
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                Extension Duration Y (Minutes) *
              </label>
              <input
                type="number"
                min="1"
                {...register("extension_duration_minutes")}
                className="w-full text-sm font-mono px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:bg-white"
              />
              <p className="text-[10px] text-slate-400 mt-1">Adds Y minutes whenever trigger condition occurs (capped at forced close).</p>
              {errors.extension_duration_minutes && <p className="text-xs text-red-600 mt-1">{errors.extension_duration_minutes.message}</p>}
            </div>
          </div>

          {/* Extension Trigger Options */}
          <div className="space-y-3 pt-2">
            <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider">
              Extension Trigger Mode Selection *
            </label>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              {/* Mode 1 */}
              <label className={`p-4 rounded-xl border cursor-pointer transition flex flex-col justify-between ${
                selectedTriggerMode === "BID_RECEIVED"
                  ? "border-indigo-600 bg-indigo-50/50 shadow-xs ring-1 ring-indigo-600"
                  : "border-slate-200 bg-slate-50/50 hover:bg-slate-50"
              }`}>
                <div>
                  <div className="flex items-center space-x-2">
                    <input
                      type="radio"
                      value="BID_RECEIVED"
                      {...register("extension_trigger_mode")}
                      className="text-indigo-600"
                    />
                    <span className="text-xs font-bold text-slate-900">Mode 1: Bid Received</span>
                  </div>
                  <p className="text-[11px] text-slate-500 mt-2 leading-relaxed">
                    Extends the auction if <strong>any supplier</strong> submits a new valid bid during the last X minutes.
                  </p>
                </div>
              </label>

              {/* Mode 2 */}
              <label className={`p-4 rounded-xl border cursor-pointer transition flex flex-col justify-between ${
                selectedTriggerMode === "ANY_RANK_CHANGE"
                  ? "border-indigo-600 bg-indigo-50/50 shadow-xs ring-1 ring-indigo-600"
                  : "border-slate-200 bg-slate-50/50 hover:bg-slate-50"
              }`}>
                <div>
                  <div className="flex items-center space-x-2">
                    <input
                      type="radio"
                      value="ANY_RANK_CHANGE"
                      {...register("extension_trigger_mode")}
                      className="text-indigo-600"
                    />
                    <span className="text-xs font-bold text-slate-900">Mode 2: Any Rank Change</span>
                  </div>
                  <p className="text-[11px] text-slate-500 mt-2 leading-relaxed">
                    Extends only if <strong>any change in supplier ranking</strong> occurs during the last X minutes.
                  </p>
                </div>
              </label>

              {/* Mode 3 */}
              <label className={`p-4 rounded-xl border cursor-pointer transition flex flex-col justify-between ${
                selectedTriggerMode === "L1_RANK_CHANGE"
                  ? "border-indigo-600 bg-indigo-50/50 shadow-xs ring-1 ring-indigo-600"
                  : "border-slate-200 bg-slate-50/50 hover:bg-slate-50"
              }`}>
                <div>
                  <div className="flex items-center space-x-2">
                    <input
                      type="radio"
                      value="L1_RANK_CHANGE"
                      {...register("extension_trigger_mode")}
                      className="text-indigo-600"
                    />
                    <span className="text-xs font-bold text-slate-900">Mode 3: L1 Rank Change</span>
                  </div>
                  <p className="text-[11px] text-slate-500 mt-2 leading-relaxed">
                    Extends only when the <strong>lowest-priced bidder (L1)</strong> is dethroned during the last X minutes.
                  </p>
                </div>
              </label>
            </div>
          </div>
        </div>

        {/* Submit Button */}
        <div className="flex justify-end space-x-3 pt-4">
          <button
            type="button"
            onClick={() => navigate(-1)}
            className="px-4 py-2 border border-slate-200 text-slate-700 rounded-lg text-sm font-medium hover:bg-slate-50 transition"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={submitting}
            className="px-6 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-sm font-semibold shadow-xs disabled:opacity-50 transition"
          >
            {submitting ? "Publishing RFQ..." : "Publish British Auction RFQ"}
          </button>
        </div>
      </form>
    </div>
  );
};
