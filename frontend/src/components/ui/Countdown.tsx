import React, { useEffect, useState } from "react";
import { Clock, AlertTriangle } from "lucide-react";

interface CountdownProps {
  targetDate: string;
  forcedCloseDate?: string;
  triggerWindowMinutes: number;
  onExpire?: () => void;
}

export const Countdown: React.FC<CountdownProps> = ({
  targetDate,
  forcedCloseDate,
  triggerWindowMinutes,
}) => {
  const [timeLeft, setTimeLeft] = useState<{
    hours: number;
    minutes: number;
    seconds: number;
    totalSeconds: number;
  }>({ hours: 0, minutes: 0, seconds: 0, totalSeconds: 0 });

  useEffect(() => {
    const calculateTime = () => {
      const now = new Date().getTime();
      const target = new Date(targetDate).getTime();
      const difference = target - now;

      if (difference <= 0) {
        setTimeLeft({ hours: 0, minutes: 0, seconds: 0, totalSeconds: 0 });
        return;
      }

      const totalSeconds = Math.floor(difference / 1000);
      const hours = Math.floor(totalSeconds / 3600);
      const minutes = Math.floor((totalSeconds % 3600) / 60);
      const seconds = totalSeconds % 60;

      setTimeLeft({ hours, minutes, seconds, totalSeconds });
    };

    calculateTime();
    const interval = setInterval(calculateTime, 1000);
    return () => clearInterval(interval);
  }, [targetDate]);

  const isInTriggerWindow = timeLeft.totalSeconds > 0 && timeLeft.totalSeconds <= triggerWindowMinutes * 60;
  const isExpired = timeLeft.totalSeconds <= 0;

  return (
    <div className={`p-4 rounded-xl border transition-all ${
      isExpired
        ? "bg-slate-50 border-slate-200 text-slate-500"
        : isInTriggerWindow
        ? "bg-amber-50/80 border-amber-300 text-amber-900 shadow-sm"
        : "bg-white border-slate-200 text-slate-800 shadow-xs"
    }`}>
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-semibold uppercase tracking-wider flex items-center gap-1.5">
          <Clock className={`h-4 w-4 ${isInTriggerWindow ? "text-amber-600 animate-spin" : "text-slate-400"}`} />
          {isExpired ? "Auction Concluded" : isInTriggerWindow ? "⚡ Trigger Window Active" : "Time Remaining"}
        </span>
        {isInTriggerWindow && (
          <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded bg-amber-200 text-amber-900">
            Last {triggerWindowMinutes}m
          </span>
        )}
      </div>

      <div className="flex items-baseline space-x-2 font-mono-num">
        <div className="flex flex-col items-center">
          <span className="text-3xl font-extrabold">{String(timeLeft.hours).padStart(2, "0")}</span>
          <span className="text-[10px] text-slate-400 uppercase font-semibold">Hours</span>
        </div>
        <span className="text-2xl font-light text-slate-400">:</span>
        <div className="flex flex-col items-center">
          <span className="text-3xl font-extrabold">{String(timeLeft.minutes).padStart(2, "0")}</span>
          <span className="text-[10px] text-slate-400 uppercase font-semibold">Min</span>
        </div>
        <span className="text-2xl font-light text-slate-400">:</span>
        <div className="flex flex-col items-center">
          <span className="text-3xl font-extrabold">{String(timeLeft.seconds).padStart(2, "0")}</span>
          <span className="text-[10px] text-slate-400 uppercase font-semibold">Sec</span>
        </div>
      </div>

      {forcedCloseDate && (
        <div className="mt-3 pt-2.5 border-t border-slate-200/60 flex items-center text-xs text-slate-500 gap-1.5">
          <AlertTriangle className="h-3.5 w-3.5 text-slate-400 shrink-0" />
          <span>Hard cutoff: <strong className="font-semibold text-slate-700">{new Date(forcedCloseDate).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</strong></span>
        </div>
      )}
    </div>
  );
};
