"use client";

import { useEffect, useState } from "react";
import EnterpriseLayout from "@/components/EnterpriseLayout";
import {
  Package,
  Search,
  Filter,
  Plus,
  ExternalLink,
  Users,
  DollarSign,
  GitBranch,
  MoreVertical,
  Grid,
  List,
} from "lucide-react";
import { toolsAPI, SaaSTool, formatCurrency } from "@/lib/enterprise-api";

const ORG_ID = "demo-org-id";

const CATEGORY_COLORS: Record<string, string> = {
  productivity: "bg-blue-100 text-blue-700",
  dev_tools: "bg-purple-100 text-purple-700",
  communication: "bg-green-100 text-green-700",
  security: "bg-red-100 text-red-700",
  hr: "bg-pink-100 text-pink-700",
  finance: "bg-amber-100 text-amber-700",
  marketing: "bg-cyan-100 text-cyan-700",
  sales: "bg-indigo-100 text-indigo-700",
  analytics: "bg-orange-100 text-orange-700",
  other: "bg-gray-100 text-gray-700",
};

export default function ToolsPage() {
  const [tools, setTools] = useState<SaaSTool[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("all");
  const [viewMode, setViewMode] = useState<"grid" | "list">("grid");
  const [categories, setCategories] = useState<Record<string, number>>({});
  const [showAddModal, setShowAddModal] = useState(false);

  useEffect(() => {
    loadTools();
    loadCategories();
  }, [categoryFilter]);

  const loadTools = async () => {
    try {
      setLoading(true);
      const params: any = { page_size: 100 };
      if (categoryFilter !== "all") params.category = categoryFilter;

      const response = await toolsAPI.list(ORG_ID, params);
      setTools(response.items);
    } catch (error) {
      console.error("Failed to load tools:", error);
    } finally {
      setLoading(false);
    }
  };

  const loadCategories = async () => {
    try {
      const response = await toolsAPI.getCategories(ORG_ID);
      setCategories(response.categories);
    } catch (error) {
      console.error("Failed to load categories:", error);
    }
  };

  const filteredTools = tools.filter((tool) =>
    tool.name.toLowerCase().includes(search.toLowerCase()) ||
    tool.vendor_domain?.toLowerCase().includes(search.toLowerCase())
  );

  const ToolCard = ({ tool }: { tool: SaaSTool }) => (
    <div className="bg-white rounded-xl border border-gray-200 p-5 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          {tool.logo_url ? (
            <img
              src={tool.logo_url}
              alt={tool.name}
              className="w-10 h-10 rounded-lg object-contain"
            />
          ) : (
            <div className="w-10 h-10 bg-gray-100 rounded-lg flex items-center justify-center">
              <Package className="w-5 h-5 text-gray-400" />
            </div>
          )}
          <div>
            <h3 className="font-semibold text-gray-900">{tool.name}</h3>
            {tool.vendor_domain && (
              <p className="text-sm text-gray-500">{tool.vendor_domain}</p>
            )}
          </div>
        </div>
        <button className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-400">
          <MoreVertical className="w-4 h-4" />
        </button>
      </div>

      <div className="flex items-center gap-2 mb-4">
        <span
          className={`px-2 py-1 rounded-full text-xs font-medium ${
            CATEGORY_COLORS[tool.category || "other"]
          }`}
        >
          {(tool.category || "other").replace(/_/g, " ")}
        </span>
        {tool.is_keystone && (
          <span className="px-2 py-1 rounded-full text-xs font-medium bg-amber-100 text-amber-700">
            Keystone
          </span>
        )}
      </div>

      <div className="grid grid-cols-3 gap-4 text-center">
        <div>
          <p className="text-lg font-semibold text-gray-900">
            {tool.active_users || 0}
          </p>
          <p className="text-xs text-gray-500">Active Users</p>
        </div>
        <div>
          <p className="text-lg font-semibold text-gray-900">
            {formatCurrency(tool.monthly_cost || 0)}
          </p>
          <p className="text-xs text-gray-500">Monthly</p>
        </div>
        <div>
          <p className="text-lg font-semibold text-gray-900">
            {tool.dependency_count || 0}
          </p>
          <p className="text-xs text-gray-500">Dependencies</p>
        </div>
      </div>

      <div className="mt-4 pt-4 border-t border-gray-100 flex items-center justify-between">
        <span
          className={`px-2 py-1 rounded text-xs font-medium ${
            tool.status === "active"
              ? "bg-green-100 text-green-700"
              : tool.status === "under_review"
              ? "bg-amber-100 text-amber-700"
              : "bg-gray-100 text-gray-700"
          }`}
        >
          {tool.status}
        </span>
        <a
          href={tool.vendor_url || `https://${tool.vendor_domain}`}
          target="_blank"
          rel="noopener noreferrer"
          className="text-sm text-blue-600 hover:text-blue-700 flex items-center gap-1"
        >
          Visit <ExternalLink className="w-3 h-3" />
        </a>
      </div>
    </div>
  );

  const ToolRow = ({ tool }: { tool: SaaSTool }) => (
    <tr className="hover:bg-gray-50">
      <td className="px-6 py-4">
        <div className="flex items-center gap-3">
          {tool.logo_url ? (
            <img
              src={tool.logo_url}
              alt={tool.name}
              className="w-8 h-8 rounded-lg object-contain"
            />
          ) : (
            <div className="w-8 h-8 bg-gray-100 rounded-lg flex items-center justify-center">
              <Package className="w-4 h-4 text-gray-400" />
            </div>
          )}
          <div>
            <p className="font-medium text-gray-900">{tool.name}</p>
            <p className="text-sm text-gray-500">{tool.vendor_domain}</p>
          </div>
        </div>
      </td>
      <td className="px-6 py-4">
        <span
          className={`px-2 py-1 rounded-full text-xs font-medium ${
            CATEGORY_COLORS[tool.category || "other"]
          }`}
        >
          {(tool.category || "other").replace(/_/g, " ")}
        </span>
      </td>
      <td className="px-6 py-4 text-sm text-gray-900">
        {tool.active_users || 0} / {tool.total_users || 0}
      </td>
      <td className="px-6 py-4 text-sm text-gray-900">
        {formatCurrency(tool.monthly_cost || 0)}
      </td>
      <td className="px-6 py-4">
        <span
          className={`px-2 py-1 rounded text-xs font-medium ${
            tool.status === "active"
              ? "bg-green-100 text-green-700"
              : "bg-gray-100 text-gray-700"
          }`}
        >
          {tool.status}
        </span>
      </td>
      <td className="px-6 py-4">
        <button className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-400">
          <MoreVertical className="w-4 h-4" />
        </button>
      </td>
    </tr>
  );

  return (
    <EnterpriseLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">SaaS Tools</h1>
            <p className="text-gray-500">
              {tools.length} tools in your organization
            </p>
          </div>
          <button
            onClick={() => setShowAddModal(true)}
            className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            <Plus className="w-4 h-4" />
            Add Tool
          </button>
        </div>

        {/* Filters */}
        <div className="bg-white rounded-xl border border-gray-200 p-4">
          <div className="flex flex-col md:flex-row gap-4">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                placeholder="Search tools..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2">
                <Filter className="w-4 h-4 text-gray-400" />
                <select
                  value={categoryFilter}
                  onChange={(e) => setCategoryFilter(e.target.value)}
                  className="px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="all">All Categories</option>
                  {Object.keys(categories).map((cat) => (
                    <option key={cat} value={cat}>
                      {cat.replace(/_/g, " ")} ({categories[cat]})
                    </option>
                  ))}
                </select>
              </div>
              <div className="flex items-center border border-gray-200 rounded-lg">
                <button
                  onClick={() => setViewMode("grid")}
                  className={`p-2 ${
                    viewMode === "grid"
                      ? "bg-gray-100 text-gray-900"
                      : "text-gray-400 hover:text-gray-600"
                  }`}
                >
                  <Grid className="w-4 h-4" />
                </button>
                <button
                  onClick={() => setViewMode("list")}
                  className={`p-2 ${
                    viewMode === "list"
                      ? "bg-gray-100 text-gray-900"
                      : "text-gray-400 hover:text-gray-600"
                  }`}
                >
                  <List className="w-4 h-4" />
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Tools display */}
        {loading ? (
          <div className="flex items-center justify-center h-64">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
          </div>
        ) : filteredTools.length === 0 ? (
          <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
            <Package className="w-12 h-12 text-gray-300 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              No tools found
            </h3>
            <p className="text-gray-500 mb-4">
              {search || categoryFilter !== "all"
                ? "Try adjusting your filters"
                : "Add your first SaaS tool to get started"}
            </p>
            <button
              onClick={() => setShowAddModal(true)}
              className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
            >
              <Plus className="w-4 h-4" />
              Add Tool
            </button>
          </div>
        ) : viewMode === "grid" ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredTools.map((tool) => (
              <ToolCard key={tool.id} tool={tool} />
            ))}
          </div>
        ) : (
          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Tool
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Category
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Users
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Cost
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Status
                  </th>
                  <th className="px-6 py-3"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {filteredTools.map((tool) => (
                  <ToolRow key={tool.id} tool={tool} />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </EnterpriseLayout>
  );
}
