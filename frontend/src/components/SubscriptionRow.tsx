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
  cancelled: "bg-zinc-500/10 text-zinc-400 border border-zinc-500/20",
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
    <tr className="hover:bg-zinc-800/50 transition-colors">
      {/* Vendor */}
      <td className="px-4 py-3">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-md bg-zinc-800 flex items-center justify-center text-zinc-400 text-sm font-medium">
            {subscription.vendor_name.charAt(0).toUpperCase()}
          </div>
          <div>
            <p className="text-sm text-zinc-200">{subscription.vendor_name}</p>
            <p className="text-xs text-zinc-500">via {subscription.source}</p>
          </div>
        </div>
      </td>

      {/* Amount */}
      <td className="px-4 py-3">
        <div>
          <p className="text-sm text-zinc-200">
            {formatCurrency(subscription.amount_cents, subscription.currency)}
          </p>
          {subscription.billing_cycle && (
            <p className="text-xs text-zinc-500">{subscription.billing_cycle}</p>
          )}
        </div>
      </td>

      {/* Status */}
      <td className="px-4 py-3">
        <span
          className={`inline-flex px-2 py-0.5 rounded text-xs font-medium ${
            statusStyles[subscription.status as keyof typeof statusStyles] ||
            statusStyles.active
          }`}
        >
          {subscription.status}
        </span>
      </td>

      {/* Last Charged */}
      <td className="px-4 py-3 text-sm text-zinc-500">
        {formatRelativeDate(subscription.last_charge_at)}
      </td>

      {/* Next Renewal */}
      <td className="px-4 py-3 text-sm text-zinc-500">
        {subscription.next_renewal_at
          ? formatRelativeDate(subscription.next_renewal_at)
          : "—"}
      </td>

      {/* Actions */}
      <td className="px-4 py-3 text-right">
        <div className="relative">
          <button
            onClick={() => setShowMenu(!showMenu)}
            className="p-1.5 text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800 rounded transition-colors"
          >
            <MoreHorizontal className="w-4 h-4" />
          </button>

          {showMenu && (
            <>
              <div
                className="fixed inset-0 z-10"
                onClick={() => setShowMenu(false)}
              />
              <div className="absolute right-0 mt-1 w-40 rounded-md border border-zinc-700 bg-zinc-800 shadow-lg py-1 z-20">
                <button
                  onClick={handleDelete}
                  disabled={deleting}
                  className="flex items-center gap-2 w-full px-3 py-1.5 text-sm text-red-400 hover:bg-zinc-700 transition-colors disabled:opacity-50"
                >
                  <Trash2 className="w-3.5 h-3.5" />
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
