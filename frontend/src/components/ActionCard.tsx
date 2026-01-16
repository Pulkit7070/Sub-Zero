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
    bg: "bg-red-50",
    border: "border-red-200",
    iconColor: "text-red-600",
    badge: "bg-red-100 text-red-700",
    label: "Consider Cancelling",
  },
  review: {
    icon: AlertTriangle,
    bg: "bg-amber-50",
    border: "border-amber-200",
    iconColor: "text-amber-600",
    badge: "bg-amber-100 text-amber-700",
    label: "Review Usage",
  },
  remind: {
    icon: Bell,
    bg: "bg-blue-50",
    border: "border-blue-200",
    iconColor: "text-blue-600",
    badge: "bg-blue-100 text-blue-700",
    label: "Renewal Reminder",
  },
  keep: {
    icon: CheckCircle,
    bg: "bg-green-50",
    border: "border-green-200",
    iconColor: "text-green-600",
    badge: "bg-green-100 text-green-700",
    label: "Keep Active",
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
    <div className={`rounded-xl border ${style.border} ${style.bg} p-5`}>
      <div className="flex items-start gap-4">
        {/* Icon */}
        <div
          className={`w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0 ${
            style.bg.replace("50", "100")
          }`}
        >
          <Icon className={`w-6 h-6 ${style.iconColor}`} />
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2 mb-1">
            <h3 className="font-semibold text-gray-900 truncate">
              {subscription?.vendor_name || "Unknown Subscription"}
            </h3>
            <span
              className={`px-2 py-0.5 rounded-full text-xs font-medium ${style.badge} flex-shrink-0`}
            >
              {style.label}
            </span>
          </div>

          {/* Subscription details */}
          <div className="flex items-center gap-3 text-sm text-gray-600 mb-2">
            {subscription?.amount_cents && (
              <span className="font-medium">
                {formatCurrency(subscription.amount_cents, subscription.currency)}
                {subscription.billing_cycle && `/${subscription.billing_cycle}`}
              </span>
            )}
            {subscription?.source && (
              <span className="text-gray-400">
                via {subscription.source}
              </span>
            )}
          </div>

          {/* Reason */}
          <p className="text-sm text-gray-700 mb-4">{decision.reason}</p>

          {/* Actions */}
          <div className="flex items-center gap-2">
            {decision.decision_type === "cancel" && (
              <>
                <button
                  onClick={() => handleAction("accepted")}
                  disabled={loading !== null}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-red-600 text-white text-sm font-medium rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50"
                >
                  {loading === "accepted" ? (
                    <span className="animate-spin">...</span>
                  ) : (
                    <Check className="w-4 h-4" />
                  )}
                  Cancel it
                </button>
                <button
                  onClick={() => handleAction("rejected")}
                  disabled={loading !== null}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white text-gray-700 text-sm font-medium rounded-lg border border-gray-300 hover:bg-gray-50 transition-colors disabled:opacity-50"
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
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-amber-600 text-white text-sm font-medium rounded-lg hover:bg-amber-700 transition-colors disabled:opacity-50"
                >
                  {loading === "accepted" ? (
                    <span className="animate-spin">...</span>
                  ) : (
                    <Check className="w-4 h-4" />
                  )}
                  Will review
                </button>
                <button
                  onClick={() => handleAction("snoozed")}
                  disabled={loading !== null}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white text-gray-700 text-sm font-medium rounded-lg border border-gray-300 hover:bg-gray-50 transition-colors disabled:opacity-50"
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
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
                >
                  {loading === "accepted" ? (
                    <span className="animate-spin">...</span>
                  ) : (
                    <Check className="w-4 h-4" />
                  )}
                  Got it
                </button>
                <button
                  onClick={() => handleAction("snoozed")}
                  disabled={loading !== null}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white text-gray-700 text-sm font-medium rounded-lg border border-gray-300 hover:bg-gray-50 transition-colors disabled:opacity-50"
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
