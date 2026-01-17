"use client";

import { useState } from "react";
import { MoreHorizontal, Trash2 } from "lucide-react";
import { Subscription, formatCurrency, formatRelativeDate } from "@/lib/api";

interface SubscriptionRowProps {
  subscription: Subscription;
  onDelete: (id: string) => Promise<void>;
}

const statusStyles = {
  active: "badge-success",
  cancelled: "bg-slate-500/15 text-slate-400 border border-slate-500/30",
  paused: "badge-warning",
  expired: "badge-danger",
};

export default function SubscriptionRow({
  subscription,
  onDelete,
}: SubscriptionRowProps) {
  const [showMenu, setShowMenu] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const handleDelete = async () => {
    if (!confirm(`Are you sure you want to remove ${subscription.vendor_name}?`)) {
      return;
    }

    setDeleting(true);
    try {
      await onDelete(subscription.id);
    } catch (error) {
      console.error("Failed to delete subscription:", error);
      alert("Failed to delete subscription");
    } finally {
      setDeleting(false);
      setShowMenu(false);
    }
  };

  return (
    <tr className="hover:bg-white/5 transition-colors">
      {/* Vendor */}
      <td className="px-6 py-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-sky-500/20 to-indigo-500/20 flex items-center justify-center text-sky-400 font-semibold">
            {subscription.vendor_name.charAt(0).toUpperCase()}
          </div>
          <div>
            <p className="font-medium text-white">{subscription.vendor_name}</p>
            <p className="text-sm text-slate-500">
              via {subscription.source}
            </p>
          </div>
        </div>
      </td>

      {/* Amount */}
      <td className="px-6 py-4">
        <div>
          <p className="font-medium text-white">
            {formatCurrency(subscription.amount_cents, subscription.currency)}
          </p>
          {subscription.billing_cycle && (
            <p className="text-sm text-slate-500">
              {subscription.billing_cycle}
            </p>
          )}
        </div>
      </td>

      {/* Status */}
      <td className="px-6 py-4">
        <span
          className={`inline-flex px-3 py-1 rounded-full text-xs font-medium ${
            statusStyles[subscription.status as keyof typeof statusStyles] ||
            statusStyles.active
          }`}
        >
          {subscription.status}
        </span>
      </td>

      {/* Last Charged */}
      <td className="px-6 py-4 text-sm text-slate-400">
        {formatRelativeDate(subscription.last_charge_at)}
      </td>

      {/* Next Renewal */}
      <td className="px-6 py-4 text-sm text-slate-400">
        {subscription.next_renewal_at
          ? formatRelativeDate(subscription.next_renewal_at)
          : "—"}
      </td>

      {/* Actions */}
      <td className="px-6 py-4 text-right">
        <div className="relative">
          <button
            onClick={() => setShowMenu(!showMenu)}
            className="p-2 text-slate-500 hover:text-white hover:bg-white/10 rounded-lg transition-colors"
          >
            <MoreHorizontal className="w-5 h-5" />
          </button>

          {showMenu && (
            <>
              <div
                className="fixed inset-0 z-10"
                onClick={() => setShowMenu(false)}
              />
              <div className="absolute right-0 mt-1 w-48 rounded-xl border border-white/10 bg-slate-800 shadow-xl py-1 z-20">
                <button
                  onClick={handleDelete}
                  disabled={deleting}
                  className="flex items-center gap-2 w-full px-4 py-2 text-sm text-red-400 hover:bg-white/5 transition-colors disabled:opacity-50"
                >
                  <Trash2 className="w-4 h-4" />
                  {deleting ? "Removing..." : "Remove"}
                </button>
              </div>
            </>
          )}
        </div>
      </td>
    </tr>
  );
}
