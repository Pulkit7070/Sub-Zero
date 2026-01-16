"use client";

import { useState } from "react";
import { MoreHorizontal, Trash2, ExternalLink } from "lucide-react";
import { Subscription, formatCurrency, formatRelativeDate } from "@/lib/api";

interface SubscriptionRowProps {
  subscription: Subscription;
  onDelete: (id: string) => Promise<void>;
}

const statusColors = {
  active: "bg-green-100 text-green-700",
  cancelled: "bg-gray-100 text-gray-700",
  paused: "bg-amber-100 text-amber-700",
  expired: "bg-red-100 text-red-700",
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
    <tr className="hover:bg-gray-50 transition-colors">
      {/* Vendor */}
      <td className="px-6 py-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-gray-100 rounded-lg flex items-center justify-center text-gray-600 font-semibold">
            {subscription.vendor_name.charAt(0).toUpperCase()}
          </div>
          <div>
            <p className="font-medium text-gray-900">{subscription.vendor_name}</p>
            <p className="text-sm text-gray-500">
              via {subscription.source}
            </p>
          </div>
        </div>
      </td>

      {/* Amount */}
      <td className="px-6 py-4">
        <div>
          <p className="font-medium text-gray-900">
            {formatCurrency(subscription.amount_cents, subscription.currency)}
          </p>
          {subscription.billing_cycle && (
            <p className="text-sm text-gray-500">
              {subscription.billing_cycle}
            </p>
          )}
        </div>
      </td>

      {/* Status */}
      <td className="px-6 py-4">
        <span
          className={`inline-flex px-2.5 py-0.5 rounded-full text-xs font-medium ${
            statusColors[subscription.status as keyof typeof statusColors] ||
            statusColors.active
          }`}
        >
          {subscription.status}
        </span>
      </td>

      {/* Last Charged */}
      <td className="px-6 py-4 text-sm text-gray-600">
        {formatRelativeDate(subscription.last_charge_at)}
      </td>

      {/* Next Renewal */}
      <td className="px-6 py-4 text-sm text-gray-600">
        {subscription.next_renewal_at
          ? formatRelativeDate(subscription.next_renewal_at)
          : "—"}
      </td>

      {/* Actions */}
      <td className="px-6 py-4 text-right">
        <div className="relative">
          <button
            onClick={() => setShowMenu(!showMenu)}
            className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <MoreHorizontal className="w-5 h-5" />
          </button>

          {showMenu && (
            <>
              <div
                className="fixed inset-0 z-10"
                onClick={() => setShowMenu(false)}
              />
              <div className="absolute right-0 mt-1 w-48 bg-white rounded-lg shadow-lg border border-gray-200 py-1 z-20">
                <button
                  onClick={handleDelete}
                  disabled={deleting}
                  className="flex items-center gap-2 w-full px-4 py-2 text-sm text-red-600 hover:bg-red-50 transition-colors disabled:opacity-50"
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
