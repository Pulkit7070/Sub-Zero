"use client";

import { useEffect, useState } from "react";
import EnterpriseLayout from "@/components/EnterpriseLayout";
import {
  Settings,
  Shield,
  Link2,
  RefreshCw,
  Check,
  X,
  ExternalLink,
  AlertTriangle,
  Building,
  Key,
} from "lucide-react";
import { integrationsAPI, organizationsAPI } from "@/lib/enterprise-api";

const ORG_ID = "demo-org-id";

interface Integration {
  id: string;
  provider: string;
  status: string;
  last_sync_at?: string;
  sync_status?: string;
}

interface Provider {
  id: string;
  name: string;
  description: string;
  features: string[];
  logo?: string;
}

const PROVIDER_LOGOS: Record<string, string> = {
  google_workspace: "https://www.gstatic.com/images/branding/product/2x/hh_google_cloud_64dp.png",
  microsoft_entra: "https://img.icons8.com/color/96/microsoft.png",
  okta: "https://www.okta.com/sites/default/files/Okta_Logo_BrightBlue_Medium.png",
  slack: "https://a.slack-edge.com/80588/marketing/img/icons/icon_slack_hash_colored.png",
};

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState<"general" | "sso" | "integrations">("general");
  const [integrations, setIntegrations] = useState<Integration[]>([]);
  const [availableProviders, setAvailableProviders] = useState<Provider[]>([]);
  const [ssoConfig, setSsoConfig] = useState<any>(null);
  const [org, setOrg] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState<string | null>(null);

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      setLoading(true);
      const [integrationsData, providersData, ssoData, orgData] = await Promise.all([
        integrationsAPI.list(ORG_ID).catch(() => ({ integrations: [] })),
        integrationsAPI.getAvailable().catch(() => ({ providers: [] })),
        integrationsAPI.getSSOConfig(ORG_ID).catch(() => null),
        organizationsAPI.get(ORG_ID).catch(() => null),
      ]);

      setIntegrations(integrationsData.integrations);
      setAvailableProviders(providersData.providers);
      setSsoConfig(ssoData);
      setOrg(orgData);
    } catch (error) {
      console.error("Failed to load settings:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleSync = async (integrationId: string) => {
    try {
      setSyncing(integrationId);
      await integrationsAPI.sync(ORG_ID, integrationId);
      await loadSettings();
    } catch (error) {
      console.error("Sync failed:", error);
      alert("Sync failed. Please try again.");
    } finally {
      setSyncing(null);
    }
  };

  const handleDisconnect = async (integrationId: string, providerName: string) => {
    if (!confirm(`Are you sure you want to disconnect ${providerName}?`)) return;

    try {
      await integrationsAPI.disconnect(ORG_ID, integrationId);
      await loadSettings();
    } catch (error) {
      console.error("Failed to disconnect:", error);
      alert("Failed to disconnect integration");
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "connected":
        return "bg-green-100 text-green-700";
      case "error":
        return "bg-red-100 text-red-700";
      default:
        return "bg-gray-100 text-gray-700";
    }
  };

  const IntegrationCard = ({ provider }: { provider: Provider }) => {
    const connected = integrations.find((i) => i.provider === provider.id);

    return (
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-center gap-4">
            <img
              src={PROVIDER_LOGOS[provider.id] || "/placeholder-logo.png"}
              alt={provider.name}
              className="w-12 h-12 object-contain"
            />
            <div>
              <h3 className="font-semibold text-gray-900">{provider.name}</h3>
              <p className="text-sm text-gray-500">{provider.description}</p>
            </div>
          </div>
          {connected ? (
            <span className={`px-2 py-1 rounded text-xs font-medium ${getStatusColor(connected.status)}`}>
              {connected.status}
            </span>
          ) : null}
        </div>

        <div className="flex flex-wrap gap-2 mb-4">
          {provider.features.map((feature) => (
            <span
              key={feature}
              className="px-2 py-1 bg-gray-100 text-gray-600 text-xs rounded"
            >
              {feature.replace(/_/g, " ")}
            </span>
          ))}
        </div>

        {connected ? (
          <div className="flex items-center justify-between pt-4 border-t border-gray-200">
            <div className="text-sm text-gray-500">
              {connected.last_sync_at
                ? `Last synced: ${new Date(connected.last_sync_at).toLocaleString()}`
                : "Never synced"}
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => handleSync(connected.id)}
                disabled={syncing === connected.id}
                className="px-3 py-1.5 text-sm bg-blue-50 text-blue-600 rounded-lg hover:bg-blue-100 disabled:opacity-50"
              >
                <RefreshCw
                  className={`w-4 h-4 inline mr-1 ${
                    syncing === connected.id ? "animate-spin" : ""
                  }`}
                />
                Sync
              </button>
              <button
                onClick={() => handleDisconnect(connected.id, provider.name)}
                className="px-3 py-1.5 text-sm bg-red-50 text-red-600 rounded-lg hover:bg-red-100"
              >
                Disconnect
              </button>
            </div>
          </div>
        ) : (
          <button className="w-full py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700">
            Connect
          </button>
        )}
      </div>
    );
  };

  if (loading) {
    return (
      <EnterpriseLayout>
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
        </div>
      </EnterpriseLayout>
    );
  }

  return (
    <EnterpriseLayout>
      <div className="space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
          <p className="text-gray-500">
            Manage your organization settings and integrations
          </p>
        </div>

        {/* Tabs */}
        <div className="border-b border-gray-200">
          <nav className="flex gap-8">
            {[
              { id: "general", label: "General", icon: Building },
              { id: "sso", label: "SSO", icon: Shield },
              { id: "integrations", label: "Integrations", icon: Link2 },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`flex items-center gap-2 py-4 border-b-2 text-sm font-medium transition-colors ${
                  activeTab === tab.id
                    ? "border-blue-600 text-blue-600"
                    : "border-transparent text-gray-500 hover:text-gray-700"
                }`}
              >
                <tab.icon className="w-4 h-4" />
                {tab.label}
              </button>
            ))}
          </nav>
        </div>

        {/* General Settings */}
        {activeTab === "general" && (
          <div className="space-y-6">
            <div className="bg-white rounded-xl border border-gray-200 p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">
                Organization Details
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Organization Name
                  </label>
                  <input
                    type="text"
                    defaultValue={org?.name || ""}
                    className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Domain
                  </label>
                  <input
                    type="text"
                    defaultValue={org?.domain || ""}
                    disabled
                    className="w-full px-4 py-2 border border-gray-200 rounded-lg bg-gray-50 text-gray-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Plan
                  </label>
                  <div className="flex items-center gap-2">
                    <span className="px-3 py-2 bg-blue-100 text-blue-700 rounded-lg font-medium capitalize">
                      {org?.plan || "trial"}
                    </span>
                    <a
                      href="#"
                      className="text-sm text-blue-600 hover:text-blue-700"
                    >
                      Upgrade
                    </a>
                  </div>
                </div>
              </div>
              <div className="mt-6 pt-6 border-t border-gray-200">
                <button className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
                  Save Changes
                </button>
              </div>
            </div>
          </div>
        )}

        {/* SSO Settings */}
        {activeTab === "sso" && (
          <div className="space-y-6">
            <div className="bg-white rounded-xl border border-gray-200 p-6">
              <div className="flex items-center justify-between mb-6">
                <div>
                  <h2 className="text-lg font-semibold text-gray-900">
                    Single Sign-On (SSO)
                  </h2>
                  <p className="text-sm text-gray-500">
                    Configure SSO for your organization
                  </p>
                </div>
                {ssoConfig?.sso_enabled ? (
                  <span className="px-3 py-1 bg-green-100 text-green-700 rounded-full text-sm font-medium">
                    <Check className="w-4 h-4 inline mr-1" />
                    Enabled
                  </span>
                ) : (
                  <span className="px-3 py-1 bg-gray-100 text-gray-600 rounded-full text-sm font-medium">
                    Disabled
                  </span>
                )}
              </div>

              {ssoConfig?.sso_enabled ? (
                <div className="space-y-4">
                  <div className="p-4 bg-gray-50 rounded-lg">
                    <div className="flex items-center gap-3">
                      <img
                        src={PROVIDER_LOGOS[ssoConfig.provider + "_workspace"] || PROVIDER_LOGOS.google_workspace}
                        alt={ssoConfig.provider}
                        className="w-10 h-10 object-contain"
                      />
                      <div>
                        <p className="font-medium text-gray-900 capitalize">
                          {ssoConfig.provider} SSO
                        </p>
                        <p className="text-sm text-gray-500">
                          Users sign in with their {ssoConfig.provider} accounts
                        </p>
                      </div>
                    </div>
                  </div>
                  <button className="text-red-600 hover:text-red-700 text-sm">
                    Disable SSO
                  </button>
                </div>
              ) : (
                <div className="space-y-4">
                  <p className="text-gray-600">
                    Enable SSO to allow your team to sign in using your identity provider.
                  </p>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {["Google", "Microsoft", "Okta", "SAML"].map((provider) => (
                      <button
                        key={provider}
                        className="p-4 border border-gray-200 rounded-lg hover:border-blue-500 hover:bg-blue-50 transition-colors text-left"
                      >
                        <p className="font-medium text-gray-900">{provider}</p>
                        <p className="text-sm text-gray-500">
                          Configure {provider} SSO
                        </p>
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>

            <div className="bg-amber-50 border border-amber-200 rounded-xl p-4">
              <div className="flex items-start gap-3">
                <AlertTriangle className="w-5 h-5 text-amber-600 mt-0.5" />
                <div>
                  <p className="font-medium text-amber-800">SSO Enforcement</p>
                  <p className="text-sm text-amber-700">
                    When SSO is enabled, all users must sign in through your identity provider.
                    Make sure to test SSO before enforcing it.
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Integrations */}
        {activeTab === "integrations" && (
          <div className="space-y-6">
            <div className="bg-blue-50 border border-blue-200 rounded-xl p-4">
              <div className="flex items-start gap-3">
                <Link2 className="w-5 h-5 text-blue-600 mt-0.5" />
                <div>
                  <p className="font-medium text-blue-800">Directory Sync</p>
                  <p className="text-sm text-blue-700">
                    Connect your identity provider to automatically sync users and discover SaaS applications.
                  </p>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {availableProviders.map((provider) => (
                <IntegrationCard key={provider.id} provider={provider} />
              ))}
            </div>
          </div>
        )}
      </div>
    </EnterpriseLayout>
  );
}
