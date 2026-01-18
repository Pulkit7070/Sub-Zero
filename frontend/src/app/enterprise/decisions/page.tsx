"use client";

import { useEffect, useState } from "react";
import EnterpriseLayout from "@/components/EnterpriseLayout";
import {
  CheckSquare,
  Search,
  Filter,
  Zap,
  TrendingDown,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Clock,
  ChevronDown,
  ChevronUp,
  Play,
  Users,
  DollarSign,
} from "lucide-react";
import {
  decisionsAPI,
  Decision,
  formatCurrency,
  formatPercent,
} from "@/lib/enterprise-api";
import { useDemoData } from "@/lib/demo-data";

const ORG_ID = "demo-org-id";
const CURRENT_USER_ID = "demo-user-id"; // In real app, get from auth
const USE_DEMO_DATA = true;

const DECISION_TYPES = {
  keep: { label: "Keep", color: "bg-green-100 text-green-700", icon: CheckCircle },
  downsize: { label: "Downsize", color: "bg-amber-100 text-amber-700", icon: TrendingDown },
  review: { label: "Review", color: "bg-blue-100 text-blue-700", icon: Clock },
  cancel: { label: "Cancel", color: "bg-red-100 text-red-700", icon: XCircle },
};

const PRIORITY_COLORS = {
  urgent: "bg-red-500",
  high: "bg-orange-500",
  normal: "bg-blue-500",
  low: "bg-gray-400",
};

export default function DecisionsPage() {
  const [decisions, setDecisions] = useState<Decision[]>([]);
  const [pendingData, setPendingData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  const [statusFilter, setStatusFilter] = useState("pending");
  const [typeFilter, setTypeFilter] = useState("all");
  const [expandedId, setExpandedId] = useState<string | null>(null);

  useEffect(() => {
    loadDecisions();
  }, [statusFilter, typeFilter]);

  const loadDecisions = async () => {
    try {
      setLoading(true);
      
      if (USE_DEMO_DATA) {
        const demoData = useDemoData();
        let filteredDecisions = demoData.decisions;
        
        if (statusFilter !== "all") {
          filteredDecisions = filteredDecisions.filter(d => d.status === statusFilter);
        }
        if (typeFilter !== "all") {
          filteredDecisions = filteredDecisions.filter(d => d.decision_type === typeFilter);
        }
        
        setDecisions(filteredDecisions);
        setPendingData({
          total_pending: demoData.decisions.filter(d => d.status === "pending").length,
          total_potential_savings_cents: demoData.decisions.reduce((sum, d) => sum + d.savings_potential_cents, 0),
          by_priority: {
            high: demoData.decisions.filter(d => d.priority === "high"),
            medium: demoData.decisions.filter(d => d.priority === "medium"),
            low: demoData.decisions.filter(d => d.priority === "low"),
          }
        });
        setLoading(false);
        return;
      }
      
      const params: any = { page_size: 100 };
      if (statusFilter !== "all") params.status = statusFilter;
      if (typeFilter !== "all") params.decision_type = typeFilter;

      const [decisionsResponse, pendingResponse] = await Promise.all([
        decisionsAPI.list(ORG_ID, params),
        decisionsAPI.getPending(ORG_ID).catch(() => null),
      ]);

      setDecisions(decisionsResponse.items);
      setPendingData(pendingResponse);
    } catch (error) {
      console.error("Failed to load decisions:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleAnalyzeAll = async () => {
    if (analyzing) return;

    try {
      setAnalyzing(true);
      
      // if (USE_DEMO_DATA) {
      //   // Simulate analysis with demo data
      //   await new Promise(resolve => setTimeout(resolve, 2000));
      //   const demoData = useDemoData();
      //   alert(`Analysis complete! Created ${demoData.decisions.length} decision recommendations.\n\n` +
      //         `💡 Quick Wins Found:\n` +
      //         `• Reduce Slack licenses: Save $1,920/month\n` +
      //         `• Cancel unused Figma seats: Save $1,440/month\n` +
      //         `• Downgrade Zoom plan: Save $950/month\n\n` +
      //         `Total Potential Savings: $${(demoData.stats.potential_savings_cents / 100).toLocaleString()}/month`);
      //   loadDecisions();
      //   setAnalyzing(false);
      //   return;
      // }
      
      const result = await decisionsAPI.analyzeAll(ORG_ID);
      alert(`Analysis complete! Created ${result.decisions_created} decision recommendations.`);
      loadDecisions();
    } catch (error) {
      console.error("Failed to analyze:", error);
      alert("Analysis failed. Please try again.");
    } finally {
      setAnalyzing(false);
    }
  };

  const handleApprove = async (decisionId: string) => {
    try {
      await decisionsAPI.approve(ORG_ID, decisionId, CURRENT_USER_ID);
      loadDecisions();
    } catch (error) {
      console.error("Failed to approve:", error);
      alert("Failed to approve decision");
    }
  };

  const handleReject = async (decisionId: string) => {
    const reason = prompt("Reason for rejection (optional):");
    try {
      await decisionsAPI.reject(ORG_ID, decisionId, CURRENT_USER_ID, reason || undefined);
      loadDecisions();
    } catch (error) {
      console.error("Failed to reject:", error);
      alert("Failed to reject decision");
    }
  };

  const handleExecute = async (decisionId: string) => {
    if (!confirm("Are you sure you want to execute this decision?")) return;

    try {
      await decisionsAPI.execute(ORG_ID, decisionId);
      loadDecisions();
    } catch (error) {
      console.error("Failed to execute:", error);
      alert("Failed to execute decision");
    }
  };

  const DecisionCard = ({ decision }: { decision: Decision }) => {
    const type = DECISION_TYPES[decision.decision_type as keyof typeof DECISION_TYPES];
    const isExpanded = expandedId === decision.id;
    const TypeIcon = type?.icon || Clock;

    return (
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div
          className="p-5 cursor-pointer hover:bg-gray-50"
          onClick={() => setExpandedId(isExpanded ? null : decision.id)}
        >
          <div className="flex items-start justify-between">
            <div className="flex items-start gap-4">
              <div className={`p-2 rounded-lg ${type?.color || "bg-gray-100"}`}>
                <TypeIcon className="w-5 h-5" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="font-semibold text-gray-900">
                    {decision.tool_name || "Unknown Tool"}
                  </h3>
                  <span
                    className={`w-2 h-2 rounded-full ${
                      PRIORITY_COLORS[decision.priority as keyof typeof PRIORITY_COLORS]
                    }`}
                  />
                </div>
                <p className="text-sm text-gray-500 mt-1">{decision.explanation}</p>
                <div className="flex items-center gap-4 mt-2">
                  <span className={`px-2 py-1 rounded text-xs font-medium ${type?.color}`}>
                    {type?.label || decision.decision_type}
                  </span>
                  {decision.savings_potential_cents > 0 && (
                    <span className="text-sm text-green-600 font-medium">
                      Save {formatCurrency(decision.savings_potential_cents)}/year
                    </span>
                  )}
                  <span className="text-sm text-gray-400">
                    Confidence: {formatPercent(decision.confidence)}
                  </span>
                </div>
              </div>
            </div>
            <div className="flex items-center gap-2">
              {decision.status === "pending" && (
                <>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleApprove(decision.id);
                    }}
                    className="p-2 rounded-lg bg-green-100 text-green-600 hover:bg-green-200"
                  >
                    <CheckCircle className="w-4 h-4" />
                  </button>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleReject(decision.id);
                    }}
                    className="p-2 rounded-lg bg-red-100 text-red-600 hover:bg-red-200"
                  >
                    <XCircle className="w-4 h-4" />
                  </button>
                </>
              )}
              {decision.status === "approved" && (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    handleExecute(decision.id);
                  }}
                  className="px-3 py-1.5 rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-700"
                >
                  <Play className="w-4 h-4 inline mr-1" />
                  Execute
                </button>
              )}
              {isExpanded ? (
                <ChevronUp className="w-5 h-5 text-gray-400" />
              ) : (
                <ChevronDown className="w-5 h-5 text-gray-400" />
              )}
            </div>
          </div>
        </div>

        {isExpanded && decision.factors && (
          <div className="px-5 pb-5 border-t border-gray-100">
            <h4 className="text-sm font-medium text-gray-700 mt-4 mb-3">
              Decision Factors
            </h4>
            <div className="space-y-2">
              {(decision.factors as any[]).map((factor, i) => (
                <div
                  key={i}
                  className="flex items-center justify-between py-2 px-3 bg-gray-50 rounded-lg"
                >
                  <div className="flex items-center gap-3">
                    <div
                      className={`w-2 h-2 rounded-full ${
                        factor.impact === "positive"
                          ? "bg-green-500"
                          : factor.impact === "negative"
                          ? "bg-red-500"
                          : "bg-gray-400"
                      }`}
                    />
                    <span className="text-sm text-gray-700">{factor.explanation}</span>
                  </div>
                  <span className="text-sm text-gray-500">
                    Weight: {formatPercent(factor.weight)}
                  </span>
                </div>
              ))}
            </div>

            {decision.recommended_seats && (
              <div className="mt-4 p-3 bg-amber-50 rounded-lg">
                <p className="text-sm text-amber-800">
                  <strong>Recommendation:</strong> Reduce seats from{" "}
                  {decision.current_seats} to {decision.recommended_seats}
                </p>
              </div>
            )}
          </div>
        )}
      </div>
    );
  };

  return (
    <EnterpriseLayout pendingDecisions={pendingData?.total_pending || 0}>
      <div className="space-y-6">
        {/* Demo Banner */}
        {USE_DEMO_DATA && (
          <div className="bg-gradient-to-r from-blue-50 to-purple-50 border border-blue-200 rounded-lg p-4">
            <div className="flex items-start gap-3">
              <div className="w-10 h-10 rounded-lg bg-blue-100 flex items-center justify-center flex-shrink-0">
                <Zap className="w-5 h-5 text-blue-600" />
              </div>
              <div className="flex-1">
                <h3 className="font-semibold text-gray-900 mb-1">
                  Demo: AI-Powered Decision Engine
                </h3>
                <p className="text-sm text-gray-600">
                  Click &quot;Run Analysis&quot; to see how our AI analyzes subscription usage patterns, 
                  identifies inactive users, and generates cost-saving recommendations with confidence scores.
                </p>
              </div>
            </div>
          </div>
        )}
        
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Decisions</h1>
            <p className="text-gray-500">
              Review and approve optimization recommendations
            </p>
          </div>
          <button
            onClick={handleAnalyzeAll}
            disabled={analyzing}
            className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            <Zap className={`w-4 h-4 ${analyzing ? "animate-pulse" : ""}`} />
            {analyzing ? "Analyzing..." : "Run Analysis"}
          </button>
        </div>

        {/* Summary Cards */}
        {pendingData && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-500">Pending Decisions</p>
                  <p className="text-2xl font-bold text-gray-900">
                    {pendingData.total_pending}
                  </p>
                </div>
                <div className="p-3 bg-amber-100 rounded-xl">
                  <Clock className="w-6 h-6 text-amber-600" />
                </div>
              </div>
            </div>

            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-500">Potential Savings</p>
                  <p className="text-2xl font-bold text-gray-900">
                    {formatCurrency(pendingData.total_potential_savings_cents || 0)}
                  </p>
                </div>
                <div className="p-3 bg-green-100 rounded-xl">
                  <DollarSign className="w-6 h-6 text-green-600" />
                </div>
              </div>
            </div>

            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-500">Urgent</p>
                  <p className="text-2xl font-bold text-gray-900">
                    {pendingData.by_priority?.urgent?.length || 0}
                  </p>
                </div>
                <div className="p-3 bg-red-100 rounded-xl">
                  <AlertTriangle className="w-6 h-6 text-red-600" />
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Filters */}
        <div className="bg-white rounded-xl border border-gray-200 p-4">
          <div className="flex flex-col md:flex-row gap-4">
            <div className="flex items-center gap-3">
              <Filter className="w-4 h-4 text-gray-400" />
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="all">All Status</option>
                <option value="pending">Pending</option>
                <option value="approved">Approved</option>
                <option value="rejected">Rejected</option>
                <option value="executed">Executed</option>
              </select>
              <select
                value={typeFilter}
                onChange={(e) => setTypeFilter(e.target.value)}
                className="px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="all">All Types</option>
                <option value="keep">Keep</option>
                <option value="downsize">Downsize</option>
                <option value="review">Review</option>
                <option value="cancel">Cancel</option>
              </select>
            </div>
          </div>
        </div>

        {/* Decisions List */}
        {loading ? (
          <div className="flex items-center justify-center h-64">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
          </div>
        ) : decisions.length === 0 ? (
          <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
            <CheckSquare className="w-12 h-12 text-gray-300 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              No decisions found
            </h3>
            <p className="text-gray-500 mb-4">
              {statusFilter !== "all" || typeFilter !== "all"
                ? "Try adjusting your filters"
                : "Run an analysis to generate optimization recommendations"}
            </p>
            <button
              onClick={handleAnalyzeAll}
              disabled={analyzing}
              className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
            >
              <Zap className="w-4 h-4" />
              Run Analysis
            </button>
          </div>
        ) : (
          <div className="space-y-4">
            {decisions.map((decision) => (
              <DecisionCard key={decision.id} decision={decision} />
            ))}
          </div>
        )}
      </div>
    </EnterpriseLayout>
  );
}
