"use client";

import { useState } from "react";
import {
  XCircle,
  AlertTriangle,
  Bell,
  CheckCircle,
  X,
  Clock,
  Check,
} from "lucide-react";
import { Decision, formatCurrency } from "@/lib/api";

interface ActionCardProps {
  decision: Decision;
  onAction: (action: "accepted" | "rejected" | "snoozed") => Promise<void>;
}

const decisionStyles = {
  cancel: {
    icon: XCircle,
    gradient: "from-red-500/20 to-red-500/5",
    iconColor: "text-red-400",
    border: "border-red-500/30",
    badge: "badge-danger",
    label: "Consider Cancelling",
    primaryBtn: "bg-red-500 hover:bg-red-600",
  },
  review: {
    icon: AlertTriangle,
    gradient: "from-amber-500/20 to-amber-500/5",
    iconColor: "text-amber-400",
    border: "border-amber-500/30",
    badge: "badge-warning",
    label: "Review Usage",
    primaryBtn: "bg-amber-500 hover:bg-amber-600",
  },
  remind: {
    icon: Bell,
    gradient: "from-sky-500/20 to-sky-500/5",
    iconColor: "text-sky-400",
    border: "border-sky-500/30",
    badge: "bg-sky-500/15 text-sky-400 border border-sky-500/30",
    label: "Renewal Reminder",
    primaryBtn: "bg-sky-500 hover:bg-sky-600",
  },
  keep: {
    icon: CheckCircle,
    gradient: "from-emerald-500/20 to-emerald-500/5",
    iconColor: "text-emerald-400",
    border: "border-emerald-500/30",
    badge: "badge-success",
    label: "Keep Active",
    primaryBtn: "bg-emerald-500 hover:bg-emerald-600",
  },
};

export default function ActionCard({ decision, onAction }: ActionCardProps) {
  const [loading, setLoading] = useState<string | null>(null);

  const style = decisionStyles[decision.decision_type] || decisionStyles.keep;
  const Icon = style.icon;
  const subscription = decision.subscription;

  const handleAction = async (action: "accepted" | "rejected" | "snoozed") => {
    setLoading(action);
    try {
      await onAction(action);
    } catch (error) {
      console.error("Failed to act on decision:", error);
    } finally {
      setLoading(null);
    }
  };

  return (
    <div className={`glass-card ${style.border} hover:scale-[1.01] transition-transform duration-300`}>
      <div className="flex items-start gap-4">
        {/* Icon */}
        <div
          className={`w-14 h-14 rounded-2xl bg-gradient-to-br ${style.gradient} flex items-center justify-center flex-shrink-0`}
        >
          <Icon className={`w-7 h-7 ${style.iconColor}`} />
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2 mb-2">
            <h3 className="font-semibold text-white text-lg truncate">
              {subscription?.vendor_name || "Unknown Subscription"}
            </h3>
            <span
              className={`px-3 py-1 rounded-full text-xs font-medium ${style.badge} flex-shrink-0`}
            >
              {style.label}
            </span>
          </div>

          {/* Subscription details */}
          <div className="flex items-center gap-3 text-sm text-slate-400 mb-3">
            {subscription?.amount_cents && (
              <span className="font-medium text-white">
                {formatCurrency(subscription.amount_cents, subscription.currency)}
                {subscription.billing_cycle && `/${subscription.billing_cycle}`}
              </span>
            )}
            {subscription?.source && (
              <span className="text-slate-500">
                via {subscription.source}
              </span>
            )}
          </div>

          {/* Reason */}
          <p className="text-sm text-slate-400 mb-5">{decision.reason}</p>

          {/* Actions */}
          <div className="flex items-center gap-3">
            {decision.decision_type === "cancel" && (
              <>
                <button
                  onClick={() => handleAction("accepted")}
                  disabled={loading !== null}
                  className={`inline-flex items-center gap-2 px-4 py-2 ${style.primaryBtn} text-white text-sm font-medium rounded-xl transition-all duration-200 disabled:opacity-50`}
                >
                  {loading === "accepted" ? (
                    <div className="w-4 h-4 rounded-full border-2 border-white/30 border-t-white animate-spin"></div>
                  ) : (
                    <Check className="w-4 h-4" />
                  )}
                  Cancel it
                </button>
                <button
                  onClick={() => handleAction("rejected")}
                  disabled={loading !== null}
                  className="btn-secondary inline-flex items-center gap-2 text-sm py-2"
                >
                  <X className="w-4 h-4" />
                  Keep it
                </button>
              </>
            )}

            {decision.decision_type === "review" && (
              <>
                <button
                  onClick={() => handleAction("accepted")}
                  disabled={loading !== null}
                  className={`inline-flex items-center gap-2 px-4 py-2 ${style.primaryBtn} text-white text-sm font-medium rounded-xl transition-all duration-200 disabled:opacity-50`}
                >
                  {loading === "accepted" ? (
                    <div className="w-4 h-4 rounded-full border-2 border-white/30 border-t-white animate-spin"></div>
                  ) : (
                    <Check className="w-4 h-4" />
                  )}
                  Will review
                </button>
                <button
                  onClick={() => handleAction("snoozed")}
                  disabled={loading !== null}
                  className="btn-secondary inline-flex items-center gap-2 text-sm py-2"
                >
                  <Clock className="w-4 h-4" />
                  Remind later
                </button>
              </>
            )}

            {decision.decision_type === "remind" && (
              <>
                <button
                  onClick={() => handleAction("accepted")}
                  disabled={loading !== null}
                  className={`inline-flex items-center gap-2 px-4 py-2 ${style.primaryBtn} text-white text-sm font-medium rounded-xl transition-all duration-200 disabled:opacity-50`}
                >
                  {loading === "accepted" ? (
                    <div className="w-4 h-4 rounded-full border-2 border-white/30 border-t-white animate-spin"></div>
                  ) : (
                    <Check className="w-4 h-4" />
                  )}
                  Got it
                </button>
                <button
                  onClick={() => handleAction("snoozed")}
                  disabled={loading !== null}
                  className="btn-secondary inline-flex items-center gap-2 text-sm py-2"
                >
                  <Clock className="w-4 h-4" />
                  Snooze
                </button>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
