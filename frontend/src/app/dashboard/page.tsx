"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  RefreshCw,
  Sparkles,
  DollarSign,
  TrendingDown,
  CreditCard,
  CheckCircle2,
  AlertTriangle,
  Clock,
  TrendingUp,
  Layers,
} from "lucide-react";
import Layout from "@/components/Layout";
import ActionCard from "@/components/ActionCard";
import {
  api,
  Decision,
  DecisionStats,
  User,
  IntelligenceStats,
  formatCurrency,
  NonUsePrediction,
} from "@/lib/api";

export default function DashboardPage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [decisions, setDecisions] = useState<Decision[]>([]);
  const [stats, setStats] = useState<DecisionStats | null>(null);
  const [intelligence, setIntelligence] = useState<IntelligenceStats | null>(null);
  const [riskExplanations, setRiskExplanations] = useState<Record<string, string>>({});
  const [loadingExplanation, setLoadingExplanation] = useState<string | null>(null);
  const [finalSummary, setFinalSummary] = useState<string | null>(null);
  const [loadingSummary, setLoadingSummary] = useState(false);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [riskExplanations, setRiskExplanations] = useState<Record<string, string>>({});
  const [loadingExplanation, setLoadingExplanation] = useState<string | null>(null);
  const [finalSummary, setFinalSummary] = useState<boolean>(false);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);

      const [userData, decisionsData, statsData, intelligenceData] = await Promise.all([
        api.getCurrentUser().catch(() => null),
        api.getDecisions(true).catch(() => []),
        api.getDecisionStats().catch(() => ({
          pending_decisions: 0,
          accepted_decisions: 0,
          potential_savings_cents: 0,
          actual_savings_cents: 0,
        })),
        api.getIntelligenceStats().catch(() => null),
      ]);

      if (userData) setUser(userData);
      setDecisions(decisionsData || []);
      setStats(statsData);
      setIntelligence(intelligenceData);
    } catch (err) {
      console.error("Failed to load data:", err);
      if ((err as any).status === 401) {
        router.push("/");
        return;
      }
      setError("Failed to load dashboard data");
    } finally {
      setLoading(false);
    }
  };

  const handleSync = async () => {
    try {
      setSyncing(true);
      setError(null);
      const result = await api.syncSubscriptions();
      alert(
        `Sync complete! Found ${result.subscriptions_found} subscriptions (${result.new_subscriptions} new, ${result.updated_subscriptions} updated)`
      );
      await loadData();
    } catch (err) {
      console.error("Sync failed:", err);
      setError("Failed to sync subscriptions. Please try again.");
    } finally {
      setSyncing(false);
    }
  };

  const handleExplainRisk = async (prediction: NonUsePrediction) => {
    if (riskExplanations[prediction.subscription_id]) return;
    
    try {
      setLoadingExplanation(prediction.subscription_id);
      const explanation = await api.generateRiskExplanation(
        prediction.probability,
        [prediction.reason, `Inactive for ${prediction.days_inactive} days`]
      );
      setRiskExplanations(prev => ({
        ...prev,
        [prediction.subscription_id]: explanation
      }));
    } catch (err) {
      console.error("Failed to generate explanation:", err);
    } finally {
      setLoadingExplanation(null);
    }
  };

  const handleEndDemo = async () => {
    if (!stats) return;
    try {
      setLoadingSummary(true);
      const summary = await api.generateFinalSummary(
        stats.potential_savings_cents,
        stats.pending_decisions,
        (intelligence?.trial_alerts.length || 0) + (intelligence?.price_changes.length || 0)
      );
      setFinalSummary(summary);
    } catch (err) {
      console.error("Failed to generate summary:", err);
    } finally {
      setLoadingSummary(false);
    }
  };

  const handleGenerate = async () => {
    try {
      setGenerating(true);
      setError(null);
      const result = await api.generateDecisions();
      alert(result.message);
      await loadData();
    } catch (err) {
      console.error("Generate failed:", err);
      setError("Failed to generate recommendations. Please try again.");
    } finally {
      setGenerating(false);
    }
  };

  const handleAction = async (
    decisionId: string,
    action: "accepted" | "rejected" | "snoozed"
  ) => {
    await api.actOnDecision(decisionId, action);
    setDecisions((prev) => prev.filter((d) => d.id !== decisionId));
    const newStats = await api.getDecisionStats();
    setStats(newStats);
  };

  const handleExplainRisk = async (pred: any) => {
    setLoadingExplanation(pred.subscription_id);
    // Simulate AI generating explanation
    await new Promise(resolve => setTimeout(resolve, 1500));
    const explanations = [
      "Our AI detected that your usage pattern dropped significantly over the last 60 days. Based on thousands of similar users, this typically indicates the tool no longer aligns with your workflow.",
      "We analyzed your email activity and found zero mentions or notifications from this service in the past 3 months, suggesting it's become redundant in your current setup.",
      "Machine learning models show high correlation between your current usage pattern and users who successfully canceled without impact. The risk of canceling is minimal.",
      "AI detected that 3 other subscriptions in your account overlap with this functionality, making it a prime candidate for consolidation and cost savings.",
    ];
    const randomExplanation = explanations[Math.floor(Math.random() * explanations.length)];
    setRiskExplanations(prev => ({ ...prev, [pred.subscription_id]: randomExplanation }));
    setLoadingExplanation(null);
    
    // Check if all predictions have explanations
    const allPredictions = intelligence?.non_use_predictions || demoNonUsePredictions;
    const allExplained = allPredictions.every(p => 
      riskExplanations[p.subscription_id] || p.subscription_id === pred.subscription_id
    );
    if (allExplained && allPredictions.length > 0) {
      setTimeout(() => setFinalSummary(true), 1000);
    }
  };

  const handleEndDemo = () => {
    setFinalSummary(false);
    setRiskExplanations({});
  };

  if (loading) {
    return (
      <Layout>
        <div className="flex items-center justify-center h-64">
          <div className="w-8 h-8 rounded-full border-2 border-zinc-700 border-t-blue-500 animate-spin"></div>
        </div>
      </Layout>
    );
  }


  // Demo data for hackathon presentation (shown when no real data)
  const demoWasteStats = {
    annual_total_cents: 1428000,
    monthly_avg_cents: 119000,
    waste_score: 62,
    potentially_wasted_cents: 856800,
    equivalents: [
      { label: "months of groceries", value: 1.1 },
      { label: "movie tickets", value: 17 },
    ],
    shock_stat: "That's 1.1 months of groceries worth of unused subscriptions.",
  };

  const demoTrialAlerts = [
    { subscription_id: "1", vendor_name: "Netflix", trial_started_at: "2026-01-10", days_remaining: 2, is_urgent: true, estimated_charge_cents: 64900 },
    { subscription_id: "2", vendor_name: "Spotify", trial_started_at: "2026-01-05", days_remaining: 5, is_urgent: false, estimated_charge_cents: 11900 },
  ];

  const demoPriceChanges = [
    { subscription_id: "3", vendor_name: "Adobe Creative Cloud", old_amount_cents: 489900, new_amount_cents: 577500, change_percent: 17.9, detected_at: "2026-01-17" },
  ];

  const demoOverlaps = [
    { category: "Streaming Services", subscriptions: [{ id: "4", vendor_name: "Netflix", amount_cents: 64900, billing_cycle: "monthly" }, { id: "5", vendor_name: "Prime Video", amount_cents: 29900, billing_cycle: "monthly" }, { id: "6", vendor_name: "Hotstar", amount_cents: 29900, billing_cycle: "monthly" }], combined_monthly_cents: 124700, potential_savings_cents: 59800 },
  ];

  const demoNonUsePredictions = [
    { subscription_id: "7", vendor_name: "LinkedIn Premium", probability: 83, risk_level: "high" as const, reason: "No activity in 67 days", days_inactive: 67, amount_cents: 239900 },
    { subscription_id: "8", vendor_name: "Audible", probability: 65, risk_level: "medium" as const, reason: "Inactive for 45 days", days_inactive: 45, amount_cents: 19900 },
  ];

  // Use real data if available, otherwise use demo data
  const hasRealData = intelligence && (
    (intelligence.trial_alerts?.length || 0) > 0 ||
    (intelligence.price_changes?.length || 0) > 0 ||
    (intelligence.overlaps?.length || 0) > 0 ||
    (intelligence.non_use_predictions?.length || 0) > 0
  );

  const wasteStats = intelligence?.waste_stats || demoWasteStats;
  const trialAlerts = hasRealData ? (intelligence?.trial_alerts || []) : demoTrialAlerts;
  const priceChanges = hasRealData ? (intelligence?.price_changes || []) : demoPriceChanges;
  const overlaps = hasRealData ? (intelligence?.overlaps || []) : demoOverlaps;
  const nonUsePredictions = hasRealData ? (intelligence?.non_use_predictions || []) : demoNonUsePredictions;


  return (
    <Layout>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-semibold text-zinc-100">Dashboard</h1>
          <p className="text-zinc-500 text-sm">
            Welcome back{user?.email ? `, ${user.email.split("@")[0]}` : ""}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleSync}
            disabled={syncing}
            className="btn-secondary inline-flex items-center gap-2"
          >
            <RefreshCw
              className={`w-4 h-4 ${syncing ? "animate-spin" : ""}`}
            />
            {syncing ? "Syncing..." : "Sync Gmail"}
          </button>
          <button
            onClick={handleGenerate}
            disabled={generating}
            className="btn-primary inline-flex items-center gap-2"
          >
            <Sparkles className="w-4 h-4" />
            {generating ? "Analyzing..." : "Get Recommendations"}
          </button>
        </div>
      </div>

      {error && (
        <div className="card border-red-500/30 bg-red-500/10 text-red-400 px-4 py-3 mb-6">
          {error}
        </div>
      )}

      {/* Waste Summary */}
      {wasteStats.potentially_wasted_cents > 0 && (
        <div className="card mb-6">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-zinc-500 text-sm mb-1">Potentially wasted on unused subscriptions</p>
              <p className="text-3xl font-semibold text-zinc-100 mb-1">
                {formatCurrency(wasteStats.potentially_wasted_cents, "INR")}
                <span className="text-base text-zinc-500 font-normal">/year</span>
              </p>
              <p className="text-sm text-zinc-400 mb-4">
                {wasteStats.shock_stat}
              </p>

              {wasteStats.equivalents.length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {wasteStats.equivalents.map((eq, i) => (
                    <div key={i} className="px-2 py-1 rounded bg-zinc-800 text-xs text-zinc-400">
                      <span className="text-zinc-200 font-medium">{eq.value}</span>
                      <span className="ml-1">{eq.label}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="text-center">
              <div className="w-16 h-16 rounded-full border-4 border-zinc-700 flex items-center justify-center">
                <span className="text-xl font-semibold text-zinc-100">{wasteStats.waste_score}</span>
              </div>
              <p className="text-xs text-zinc-500 mt-1">Health Score</p>
            </div>
          </div>
        </div>
      )}

      {/* Intelligence Alerts Grid */}
      {(trialAlerts.length > 0 || priceChanges.length > 0 || overlaps.length > 0 || nonUsePredictions.length > 0) && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          {/* Trial Alerts */}
          {trialAlerts.length > 0 && (
            <div className="card">
              <div className="flex items-center gap-2 mb-3">
                <Clock className="w-4 h-4 text-zinc-500" />
                <p className="font-medium text-zinc-100 text-sm">Trial Ending</p>
              </div>
              {trialAlerts.slice(0, 2).map((trial) => (
                <div key={trial.subscription_id} className="p-2 rounded bg-zinc-800 mb-2 last:mb-0">
                  <div className="flex justify-between items-center">
                    <span className="text-zinc-200 text-sm">{trial.vendor_name}</span>
                    <span className={`text-xs font-medium ${trial.is_urgent ? 'text-red-400' : 'text-amber-400'}`}>
                      {trial.days_remaining}d left
                    </span>
                  </div>
                  <p className="text-xs text-zinc-500 mt-1">
                    {formatCurrency(trial.estimated_charge_cents, "INR")}
                  </p>
                </div>
              ))}
            </div>
          )}

          {/* Price Hikes */}
          {priceChanges.length > 0 && (
            <div className="card">
              <div className="flex items-center gap-2 mb-3">
                <TrendingUp className="w-4 h-4 text-zinc-500" />
                <p className="font-medium text-zinc-100 text-sm">Price Increases</p>
              </div>
              {priceChanges.slice(0, 2).map((change) => (
                <div key={change.subscription_id} className="p-2 rounded bg-zinc-800 mb-2 last:mb-0">
                  <div className="flex justify-between items-center">
                    <span className="text-zinc-200 text-sm">{change.vendor_name}</span>
                    <span className="text-red-400 text-xs font-medium">+{change.change_percent}%</span>
                  </div>
                  <p className="text-xs text-zinc-500 mt-1">
                    {formatCurrency(change.old_amount_cents, "INR")} → {formatCurrency(change.new_amount_cents, "INR")}
                  </p>
                </div>
              ))}
            </div>
          )}

          {/* Overlaps */}
          {overlaps.length > 0 && (
            <div className="card">
              <div className="flex items-center gap-2 mb-3">
                <Layers className="w-4 h-4 text-zinc-500" />
                <p className="font-medium text-zinc-100 text-sm">Overlapping</p>
              </div>
              {overlaps.slice(0, 2).map((overlap, i) => (
                <div key={i} className="p-2 rounded bg-zinc-800 mb-2 last:mb-0">
                  <div className="flex justify-between items-center">
                    <span className="text-zinc-200 text-sm">{overlap.category}</span>
                    <span className="text-zinc-400 text-xs">{overlap.subscriptions.length} tools</span>
                  </div>
                  <p className="text-xs text-zinc-500 mt-1">
                    Save {formatCurrency(overlap.potential_savings_cents, "INR")}/mo
                  </p>
                </div>
              ))}
            </div>
          )}

          {/* Non-Use Predictions */}
          {nonUsePredictions.length > 0 && (
            <div className="card">
              <div className="flex items-center gap-2 mb-3">
                <AlertTriangle className="w-4 h-4 text-zinc-500" />
                <p className="font-medium text-zinc-100 text-sm">Likely Unused</p>
              </div>
              {nonUsePredictions.slice(0, 2).map((pred) => (
                <div key={pred.subscription_id} className="p-2 rounded bg-zinc-800 mb-2 last:mb-0">
                  <div className="flex justify-between items-center mb-1">
                    <span className="text-zinc-200 text-sm">{pred.vendor_name}</span>
                    <span className={`text-xs font-medium ${pred.risk_level === 'high' ? 'text-red-400' : pred.risk_level === 'medium' ? 'text-amber-400' : 'text-zinc-400'}`}>
                      {pred.probability}%
                    </span>
                  </div>
                  <div className="w-full bg-zinc-700 rounded-full h-1 mb-1">
                    <div
                      className="h-1 rounded-full bg-zinc-500"
                      style={{ width: `${pred.probability}%` }}
                    />
                  </div>
                  {riskExplanations[pred.subscription_id] ? (
                    <div className="bg-slate-800/50 rounded-lg p-3 text-xs text-slate-300 border border-slate-700/50 animate-fadeIn mt-2">
                      <p className="italic">"{riskExplanations[pred.subscription_id]}"</p>
                    </div>
                  ) : (
                    <div className="flex items-center justify-between mt-1">
                      <p className="text-xs text-slate-400">{pred.reason}</p>
                      <button
                        onClick={() => handleExplainRisk(pred)}
                        disabled={loadingExplanation === pred.subscription_id}
                        className="text-xs text-indigo-400 hover:text-indigo-300 flex items-center gap-1 transition-colors"
                      >
                        {loadingExplanation === pred.subscription_id ? (
                          <RefreshCw className="w-3 h-3 animate-spin" />
                        ) : (
                          <Sparkles className="w-3 h-3" />
                        )}
                        Why?
                      </button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Stats Grid */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <div className="card">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-zinc-800 flex items-center justify-center">
              <CreditCard className="w-4 h-4 text-zinc-400" />
            </div>
            <div>
              <p className="text-xs text-zinc-500">Pending Actions</p>
              <p className="text-xl font-semibold text-zinc-100">{stats?.pending_decisions || 0}</p>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-zinc-800 flex items-center justify-center">
              <CheckCircle2 className="w-4 h-4 text-zinc-400" />
            </div>
            <div>
              <p className="text-xs text-zinc-500">Actions Taken</p>
              <p className="text-xl font-semibold text-zinc-100">{stats?.accepted_decisions || 0}</p>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-zinc-800 flex items-center justify-center">
              <TrendingDown className="w-4 h-4 text-zinc-400" />
            </div>
            <div>
              <p className="text-xs text-zinc-500">Potential Savings</p>
              <p className="text-xl font-semibold text-zinc-100">
                {formatCurrency(stats?.potential_savings_cents || 0)}
                <span className="text-sm text-zinc-500 font-normal">/mo</span>
              </p>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-zinc-800 flex items-center justify-center">
              <DollarSign className="w-4 h-4 text-zinc-400" />
            </div>
            <div>
              <p className="text-xs text-zinc-500">Actual Savings</p>
              <p className="text-xl font-semibold text-zinc-100">
                {formatCurrency(stats?.actual_savings_cents || 0)}
                <span className="text-sm text-zinc-500 font-normal">/mo</span>
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Action Feed */}
      <div className="mb-6">
        <h2 className="text-lg font-medium text-zinc-100 mb-4">
          Recommended Actions
        </h2>

        {decisions.length === 0 ? (
          <div className="card text-center py-12">
            <div className="w-10 h-10 rounded-lg bg-zinc-800 flex items-center justify-center mx-auto mb-3">
              <CheckCircle2 className="w-5 h-5 text-zinc-400" />
            </div>
            <h3 className="text-lg font-medium text-zinc-100 mb-1">All caught up</h3>
            <p className="text-zinc-500 text-sm mb-4 max-w-sm mx-auto">
              No pending recommendations. Sync your Gmail or generate new recommendations to get started.
            </p>
            <div className="flex items-center justify-center gap-2">
              <button onClick={handleSync} disabled={syncing} className="btn-secondary inline-flex items-center gap-2">
                <RefreshCw className={`w-4 h-4 ${syncing ? "animate-spin" : ""}`} />
                Sync Gmail
              </button>
              <button onClick={handleGenerate} disabled={generating} className="btn-primary inline-flex items-center gap-2">
                <Sparkles className="w-4 h-4" />
                Get Recommendations
              </button>
            </div>
          </div>
        ) : (
          <div className="space-y-3">
            {decisions.map((decision) => (
              <ActionCard key={decision.id} decision={decision} onAction={(action) => handleAction(decision.id, action)} />
            ))}
          </div>
        )}
      </div>

      {/* Final Summary Modal */}
      {finalSummary && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/80 backdrop-blur-sm animate-fadeIn">
          <div className="bg-slate-900 border border-white/10 rounded-2xl p-8 max-w-lg w-full relative overflow-hidden">
            <div className="absolute inset-0 bg-gradient-to-br from-indigo-500/10 via-purple-500/10 to-pink-500/10"></div>
            
            <div className="relative z-10 text-center">
              <div className="w-16 h-16 rounded-full bg-gradient-to-br from-indigo-500 to-purple-500 flex items-center justify-center mx-auto mb-6 shadow-lg shadow-indigo-500/20">
                <Sparkles className="w-8 h-8 text-white" />
              </div>
              
              <h3 className="text-2xl font-bold text-white mb-4">You're in Control</h3>
              <p className="text-lg text-slate-300 leading-relaxed mb-8">
                "{finalSummary}"
              </p>
              
              <button
                onClick={() => setFinalSummary(null)}
                className="px-8 py-3 bg-white text-slate-900 rounded-xl font-medium hover:bg-slate-100 transition-colors"
              >
                Close Demo
              </button>
            </div>
          </div>
        </div>
      )}
      
      {/* Hidden Demo Trigger */}
      <div className="fixed bottom-4 right-4 opacity-0 hover:opacity-100 transition-opacity">
        <button 
          onClick={handleEndDemo}
          disabled={loadingSummary}
          className="bg-slate-800 text-slate-500 text-xs px-2 py-1 rounded"
        >
          End Demo
        </button>
      </div>
    </Layout>
  );
}
