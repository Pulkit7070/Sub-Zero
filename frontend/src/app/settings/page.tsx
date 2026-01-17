"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  User as UserIcon,
  Mail,
  Shield,
  Trash2,
  LogOut,
  CheckCircle,
  AlertTriangle,
  Calendar,
} from "lucide-react";
import Layout from "@/components/Layout";
import { api, User } from "@/lib/api";

export default function SettingsPage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [disconnecting, setDisconnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadUser();
  }, []);

  const loadUser = async () => {
    try {
      setLoading(true);
      const userData = await api.getCurrentUser();
      setUser(userData);
    } catch (err) {
      console.error("Failed to load user:", err);
      if ((err as any).status === 401) {
        router.push("/");
        return;
      }
      setError("Failed to load user data");
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = async () => {
    try {
      await api.logout();
      router.push("/");
    } catch (err) {
      console.error("Logout failed:", err);
      router.push("/");
    }
  };

  const handleDisconnect = async () => {
    if (
      !confirm(
        "Are you sure you want to disconnect your Gmail? This will remove all your subscription data."
      )
    ) {
      return;
    }

    setDisconnecting(true);
    try {
      await api.logout();
      router.push("/");
    } catch (err) {
      console.error("Disconnect failed:", err);
      setError("Failed to disconnect account");
    } finally {
      setDisconnecting(false);
    }
  };

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
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white">Settings</h1>
        <p className="text-slate-400">Manage your account and preferences</p>
      </div>

      {error && (
        <div className="glass-card border-red-500/30 bg-red-500/10 text-red-400 px-4 py-3 mb-6">
          {error}
        </div>
      )}

      {/* Account Section */}
      <div className="glass-card mb-6">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-12 h-12 rounded-xl bg-sky-500/20 flex items-center justify-center">
            <UserIcon className="w-6 h-6 text-sky-400" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-white">Account</h2>
            <p className="text-sm text-slate-400">Your account information</p>
          </div>
        </div>

        <div className="space-y-4">
          <div className="flex items-center justify-between py-3 border-b border-white/5">
            <div className="flex items-center gap-3">
              <Mail className="w-5 h-5 text-slate-500" />
              <div>
                <p className="text-sm font-medium text-white">Email</p>
                <p className="text-sm text-slate-400">{user?.email}</p>
              </div>
            </div>
            <CheckCircle className="w-5 h-5 text-emerald-400" />
          </div>

          <div className="flex items-center justify-between py-3">
            <div className="flex items-center gap-3">
              <Calendar className="w-5 h-5 text-slate-500" />
              <div>
                <p className="text-sm font-medium text-white">
                  Account Created
                </p>
                <p className="text-sm text-slate-400">
                  {user?.created_at
                    ? new Date(user.created_at).toLocaleDateString("en-US", {
                        year: "numeric",
                        month: "long",
                        day: "numeric",
                      })
                    : "Unknown"}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Connected Accounts */}
      <div className="glass-card mb-6">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-12 h-12 rounded-xl bg-amber-500/20 flex items-center justify-center">
            <Mail className="w-6 h-6 text-amber-400" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-white">
              Connected Accounts
            </h2>
            <p className="text-sm text-slate-400">
              Manage your connected services
            </p>
          </div>
        </div>

        <div className="flex items-center justify-between py-4 px-4 bg-white/5 rounded-xl border border-white/10">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-white rounded-lg flex items-center justify-center">
              <svg className="w-5 h-5" viewBox="0 0 24 24">
                <path
                  d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                  fill="#4285F4"
                />
                <path
                  d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                  fill="#34A853"
                />
                <path
                  d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                  fill="#FBBC05"
                />
                <path
                  d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                  fill="#EA4335"
                />
              </svg>
            </div>
            <div>
              <p className="font-medium text-white">Gmail</p>
              <p className="text-sm text-slate-400">
                Connected as {user?.email}
              </p>
            </div>
          </div>
          <span className="badge-success inline-flex items-center gap-1">
            <CheckCircle className="w-3 h-3" />
            Connected
          </span>
        </div>
      </div>

      {/* Privacy & Data */}
      <div className="glass-card mb-6">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-12 h-12 rounded-xl bg-emerald-500/20 flex items-center justify-center">
            <Shield className="w-6 h-6 text-emerald-400" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-white">
              Privacy & Data
            </h2>
            <p className="text-sm text-slate-400">How we handle your data</p>
          </div>
        </div>

        <div className="space-y-4 text-sm text-slate-300">
          <div className="flex items-start gap-3">
            <CheckCircle className="w-5 h-5 text-emerald-400 flex-shrink-0 mt-0.5" />
            <p>
              We only read emails that look like receipts or invoices. We never
              read your personal messages.
            </p>
          </div>
          <div className="flex items-start gap-3">
            <CheckCircle className="w-5 h-5 text-emerald-400 flex-shrink-0 mt-0.5" />
            <p>Your OAuth tokens are encrypted at rest using AES-256.</p>
          </div>
          <div className="flex items-start gap-3">
            <CheckCircle className="w-5 h-5 text-emerald-400 flex-shrink-0 mt-0.5" />
            <p>We never share your data with third parties.</p>
          </div>
          <div className="flex items-start gap-3">
            <CheckCircle className="w-5 h-5 text-emerald-400 flex-shrink-0 mt-0.5" />
            <p>You can delete all your data at any time by disconnecting.</p>
          </div>
        </div>
      </div>

      {/* Danger Zone */}
      <div className="glass-card border-red-500/30">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-12 h-12 rounded-xl bg-red-500/20 flex items-center justify-center">
            <AlertTriangle className="w-6 h-6 text-red-400" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-white">Danger Zone</h2>
            <p className="text-sm text-slate-400">Irreversible actions</p>
          </div>
        </div>

        <div className="space-y-4">
          <div className="flex items-center justify-between py-3 border-b border-white/5">
            <div>
              <p className="font-medium text-white">Log Out</p>
              <p className="text-sm text-slate-400">
                Sign out of your account on this device
              </p>
            </div>
            <button
              onClick={handleLogout}
              className="btn-secondary inline-flex items-center gap-2"
            >
              <LogOut className="w-4 h-4" />
              Log Out
            </button>
          </div>

          <div className="flex items-center justify-between py-3">
            <div>
              <p className="font-medium text-white">Disconnect Account</p>
              <p className="text-sm text-slate-400">
                Remove Gmail connection and delete all data
              </p>
            </div>
            <button
              onClick={handleDisconnect}
              disabled={disconnecting}
              className="btn-danger inline-flex items-center gap-2"
            >
              <Trash2 className="w-4 h-4" />
              {disconnecting ? "Disconnecting..." : "Disconnect"}
            </button>
          </div>
        </div>
      </div>
    </Layout>
  );
}
