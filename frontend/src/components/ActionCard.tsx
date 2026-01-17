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
    badge: "badge-danger",
    label: "Consider Cancelling",
    primaryBtn: "bg-red-600 hover:bg-red-500",
  },
  review: {
    icon: AlertTriangle,
    badge: "badge-warning",
    label: "Review Usage",
    primaryBtn: "bg-amber-600 hover:bg-amber-500",
  },
  remind: {
    icon: Bell,
    badge: "bg-blue-500/10 text-blue-400 border border-blue-500/20",
    label: "Renewal Reminder",
    primaryBtn: "bg-blue-600 hover:bg-blue-500",
  },
  keep: {
    icon: CheckCircle,
    badge: "badge-success",
    label: "Keep Active",
    primaryBtn: "bg-emerald-600 hover:bg-emerald-500",
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
    <div className="card">
      <div className="flex items-start gap-3">
        {/* Icon */}
        <div className="w-9 h-9 rounded-lg bg-zinc-800 flex items-center justify-center flex-shrink-0">
          <Icon className="w-4 h-4 text-zinc-400" />
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2 mb-1">
            <h3 className="font-medium text-zinc-100 truncate">
              {subscription?.vendor_name || "Unknown Subscription"}
            </h3>
            <span className={`px-2 py-0.5 rounded text-xs font-medium ${style.badge} flex-shrink-0`}>
              {style.label}
            </span>
          </div>

          {/* Subscription details */}
          <div className="flex items-center gap-2 text-sm text-zinc-500 mb-2">
            {subscription?.amount_cents && (
              <span className="text-zinc-300">
                {formatCurrency(subscription.amount_cents, subscription.currency)}
                {subscription.billing_cycle && `/${subscription.billing_cycle}`}
              </span>
            )}
            {subscription?.source && (
              <span>via {subscription.source}</span>
            )}
          </div>

          {/* Reason */}
          <p className="text-sm text-zinc-500 mb-4">{decision.reason}</p>

          {/* Actions */}
          <div className="flex items-center gap-2">
            {decision.decision_type === "cancel" && (
              <>
                <button
                  onClick={() => handleAction("accepted")}
                  disabled={loading !== null}
                  className={`inline-flex items-center gap-1.5 px-3 py-1.5 ${style.primaryBtn} text-white text-sm font-medium rounded-md transition-colors disabled:opacity-50`}
                >
                  {loading === "accepted" ? (
                    <div className="w-3 h-3 rounded-full border-2 border-white/30 border-t-white animate-spin"></div>
                  ) : (
                    <Check className="w-3 h-3" />
                  )}
                  Cancel it
                </button>
                <button
                  onClick={() => handleAction("rejected")}
                  disabled={loading !== null}
                  className="btn-secondary inline-flex items-center gap-1.5 text-sm py-1.5 px-3"
                >
                  <X className="w-3 h-3" />
                  Keep it
                </button>
              </>
            )}

            {decision.decision_type === "review" && (
              <>
                <button
                  onClick={() => handleAction("accepted")}
                  disabled={loading !== null}
                  className={`inline-flex items-center gap-1.5 px-3 py-1.5 ${style.primaryBtn} text-white text-sm font-medium rounded-md transition-colors disabled:opacity-50`}
                >
                  {loading === "accepted" ? (
                    <div className="w-3 h-3 rounded-full border-2 border-white/30 border-t-white animate-spin"></div>
                  ) : (
                    <Check className="w-3 h-3" />
                  )}
                  Will review
                </button>
                <button
                  onClick={() => handleAction("snoozed")}
                  disabled={loading !== null}
                  className="btn-secondary inline-flex items-center gap-1.5 text-sm py-1.5 px-3"
                >
                  <Clock className="w-3 h-3" />
                  Remind later
                </button>
              </>
            )}

            {decision.decision_type === "remind" && (
              <>
                <button
                  onClick={() => handleAction("accepted")}
                  disabled={loading !== null}
                  className={`inline-flex items-center gap-1.5 px-3 py-1.5 ${style.primaryBtn} text-white text-sm font-medium rounded-md transition-colors disabled:opacity-50`}
                >
                  {loading === "accepted" ? (
                    <div className="w-3 h-3 rounded-full border-2 border-white/30 border-t-white animate-spin"></div>
                  ) : (
                    <Check className="w-3 h-3" />
                  )}
                  Got it
                </button>
                <button
                  onClick={() => handleAction("snoozed")}
                  disabled={loading !== null}
                  className="btn-secondary inline-flex items-center gap-1.5 text-sm py-1.5 px-3"
                >
                  <Clock className="w-3 h-3" />
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
