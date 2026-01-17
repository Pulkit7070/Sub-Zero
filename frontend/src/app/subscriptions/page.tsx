"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { RefreshCw, Search, Filter, CreditCard, Inbox } from "lucide-react";
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
    const force = true;
    try {
      setSyncing(true);
      setError(null);
      const result = await api.syncSubscriptions(90, force);
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

  const filteredSubscriptions = subscriptions.filter((sub) => {
    const matchesSearch = sub.vendor_name
      .toLowerCase()
      .includes(search.toLowerCase());
    const matchesStatus =
      statusFilter === "all" || sub.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const activeSubscriptions = subscriptions.filter(
    (s) => s.status === "active"
  );
  const monthlyTotal = activeSubscriptions.reduce((sum, s) => {
    if (!s.amount_cents) return sum;
    if (s.billing_cycle === "yearly") {
      return sum + Math.round(s.amount_cents / 12);
    }
    return sum + s.amount_cents;
  }, 0);

  if (loading) {
    return (
      <Layout>
        <div className="flex items-center justify-center h-64">
          <div className="w-12 h-12 rounded-full border-2 border-sky-500/30 border-t-sky-500 animate-spin"></div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-white mb-1">Subscriptions</h1>
          <p className="text-slate-400">
            {activeSubscriptions.length} active subscriptions totaling{" "}
            <span className="text-emerald-400 font-semibold">{formatCurrency(monthlyTotal)}/month</span>
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
        <div className="glass-card border-red-500/30 bg-red-500/10 text-red-400 px-4 py-3 mb-6">
          {error}
        </div>
      )}

      {/* Filters */}
      <div className="flex items-center gap-4 mb-6">
        <div className="flex-1 relative">
          <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 w-5 h-5 text-slate-500" />
          <input
            type="text"
            placeholder="Search subscriptions..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="input pl-12"
          />
        </div>
        <div className="flex items-center gap-2">
          <Filter className="w-5 h-5 text-slate-500" />
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
        <div className="glass-card text-center py-16">
          <div className="w-16 h-16 rounded-2xl bg-slate-500/20 flex items-center justify-center mx-auto mb-5">
            <Inbox className="w-8 h-8 text-slate-400" />
          </div>
          <h3 className="text-xl font-semibold text-white mb-2">
            No subscriptions found
          </h3>
          <p className="text-slate-400 mb-6 max-w-md mx-auto">
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
        <div className="glass-card p-0 overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-white/5">
                <th className="px-6 py-4 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  Subscription
                </th>
                <th className="px-6 py-4 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  Amount
                </th>
                <th className="px-6 py-4 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-4 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  Last Charged
                </th>
                <th className="px-6 py-4 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  Next Renewal
                </th>
                <th className="px-6 py-4 text-right text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
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
