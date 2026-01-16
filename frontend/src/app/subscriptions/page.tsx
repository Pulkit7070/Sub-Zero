"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { RefreshCw, Search, Filter, CreditCard } from "lucide-react";
import Layout from "@/components/Layout";
import SubscriptionRow from "@/components/SubscriptionRow";
import { api, Subscription, formatCurrency } from "@/lib/api";

export default function SubscriptionsPage() {
  const router = useRouter();
  const [subscriptions, setSubscriptions] = useState<Subscription[]>([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");

  useEffect(() => {
    loadSubscriptions();
  }, []);

  const loadSubscriptions = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.getSubscriptions();
      setSubscriptions(data);
    } catch (err) {
      console.error("Failed to load subscriptions:", err);
      if ((err as any).status === 401) {
        router.push("/");
        return;
      }
      setError("Failed to load subscriptions");
    } finally {
      setLoading(false);
    }
  };

  const handleSync = async () => {
    const force = true; // Always do full sync
    try {
      setSyncing(true);
      setError(null);
      const result = await api.syncSubscriptions(90, force);  // 90 days max
      const syncType = result.is_incremental ? "incremental" : "full";
      alert(
        `Sync complete! Found ${result.subscriptions_found} subscriptions (${result.new_subscriptions} new, ${result.updated_subscriptions} updated)\n` +
        `Processed ${result.emails_processed} emails, skipped ${result.emails_skipped} already processed`
      );
      await loadSubscriptions();
    } catch (err) {
      console.error("Sync failed:", err);
      setError("Failed to sync subscriptions");
    } finally {
      setSyncing(false);
    }
  };

  const handleDelete = async (id: string) => {
    await api.deleteSubscription(id);
    setSubscriptions((prev) => prev.filter((s) => s.id !== id));
  };

  // Filter subscriptions
  const filteredSubscriptions = subscriptions.filter((sub) => {
    const matchesSearch = sub.vendor_name
      .toLowerCase()
      .includes(search.toLowerCase());
    const matchesStatus =
      statusFilter === "all" || sub.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  // Calculate totals
  const activeSubscriptions = subscriptions.filter(
    (s) => s.status === "active"
  );
  const monthlyTotal = activeSubscriptions.reduce((sum, s) => {
    if (!s.amount_cents) return sum;
    // Convert yearly to monthly
    if (s.billing_cycle === "yearly") {
      return sum + Math.round(s.amount_cents / 12);
    }
    return sum + s.amount_cents;
  }, 0);

  if (loading) {
    return (
      <Layout>
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Subscriptions</h1>
          <p className="text-gray-600">
            {activeSubscriptions.length} active subscriptions totaling{" "}
            {formatCurrency(monthlyTotal)}/month
          </p>
        </div>
        <button
          onClick={handleSync}
          disabled={syncing}
          className="btn-primary inline-flex items-center gap-2"
        >
          <RefreshCw className={`w-4 h-4 ${syncing ? "animate-spin" : ""}`} />
          {syncing ? "Syncing..." : "Sync Gmail"}
        </button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-6">
          {error}
        </div>
      )}

      {/* Filters */}
      <div className="flex items-center gap-4 mb-6">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
          <input
            type="text"
            placeholder="Search subscriptions..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="input pl-10"
          />
        </div>
        <div className="flex items-center gap-2">
          <Filter className="w-5 h-5 text-gray-400" />
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="input w-auto"
          >
            <option value="all">All Status</option>
            <option value="active">Active</option>
            <option value="cancelled">Cancelled</option>
            <option value="paused">Paused</option>
          </select>
        </div>
      </div>

      {/* Table */}
      {filteredSubscriptions.length === 0 ? (
        <div className="card text-center py-12">
          <CreditCard className="w-12 h-12 text-gray-300 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">
            No subscriptions found
          </h3>
          <p className="text-gray-600 mb-4">
            {subscriptions.length === 0
              ? "Sync your Gmail to find your subscriptions automatically."
              : "Try adjusting your search or filter."}
          </p>
          {subscriptions.length === 0 && (
            <button
              onClick={handleSync}
              disabled={syncing}
              className="btn-primary inline-flex items-center gap-2"
            >
              <RefreshCw
                className={`w-4 h-4 ${syncing ? "animate-spin" : ""}`}
              />
              Sync Gmail
            </button>
          )}
        </div>
      ) : (
        <div className="card p-0 overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Subscription
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Amount
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Last Charged
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Next Renewal
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {filteredSubscriptions.map((subscription) => (
                <SubscriptionRow
                  key={subscription.id}
                  subscription={subscription}
                  onDelete={handleDelete}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Layout>
  );
}
