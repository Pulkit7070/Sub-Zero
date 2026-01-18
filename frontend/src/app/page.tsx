"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Snowflake, Mail, DollarSign, TrendingDown, CheckCircle, Shield, ArrowRight, Building2 } from "lucide-react";
import { api } from "@/lib/api";

export default function LandingPage() {
  const router = useRouter();
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    api.getCurrentUser()
      .then(() => {
        router.push("/dashboard");
      })
      .catch(() => {
        setChecking(false);
      });
  }, [router]);

  if (checking) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="w-8 h-8 rounded-full border-2 border-zinc-700 border-t-blue-500 animate-spin"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      <div className="max-w-6xl mx-auto px-8 py-12">
        {/* Header */}
        <header className="flex items-center justify-between mb-24">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-blue-600 flex items-center justify-center shadow-lg shadow-blue-500/20">
              <Snowflake className="w-6 h-6 text-white" />
            </div>
            <span className="text-2xl font-semibold text-zinc-100">Sub-Zero</span>
          </div>
        </header>

        {/* Hero */}
        <div className="text-center max-w-3xl mx-auto mb-24">
          <h1 className="text-5xl md:text-6xl font-bold mb-6 text-zinc-100 leading-tight">
            Take control of your subscriptions
          </h1>

          <p className="text-xl text-zinc-400 mb-12 max-w-2xl mx-auto leading-relaxed">
            Connect your Gmail to automatically discover all your subscriptions.
            Get smart recommendations and save money on services you don&apos;t use.
          </p>

          {/* Personal vs Enterprise Choice */}
          <div className="grid md:grid-cols-2 gap-8 max-w-4xl mx-auto mb-12">
            {/* Personal */}
            <div className="card hover:border-blue-500/50 hover:shadow-lg hover:shadow-blue-500/10 transition-all cursor-pointer group">
              <div className="p-8">
                <div className="w-16 h-16 rounded-xl bg-gradient-to-br from-blue-500 to-blue-600 flex items-center justify-center mb-6 mx-auto shadow-lg shadow-blue-500/30">
                  <Mail className="w-8 h-8 text-white" />
                </div>
                <h3 className="text-2xl font-semibold text-zinc-100 mb-3">Personal</h3>
                <p className="text-zinc-400 text-base mb-6 leading-relaxed">
                  Manage your personal subscriptions with AI-powered insights
                </p>
                <a
                  href={api.getLoginUrl()}
                  className="btn-primary inline-flex items-center gap-2 px-4 py-2 w-full justify-center group-hover:bg-blue-600"
                >
                  <Mail className="w-4 h-4" />
                  Connect Gmail
                  <ArrowRight className="w-4 h-4" />
                </a>
              </div>
            </div>

            {/* Enterprise */}
            <div className="card hover:border-purple-500/50 hover:shadow-lg hover:shadow-purple-500/10 transition-all cursor-pointer group">
              <div className="p-8">
                <div className="w-16 h-16 rounded-xl bg-gradient-to-br from-purple-500 to-purple-600 flex items-center justify-center mb-6 mx-auto shadow-lg shadow-purple-500/30">
                  <Building2 className="w-6 h-6 text-white" />
                </div>
                <h3 className="text-xl font-semibold text-zinc-100 mb-2">Enterprise</h3>
                <p className="text-zinc-400 text-sm mb-4">
                  Centralized control for your organization&apos;s subscriptions
                </p>
                <a
                  href="/enterprise"
                  className="btn-primary inline-flex items-center gap-2 px-4 py-2 w-full justify-center bg-purple-500 hover:bg-purple-600 group-hover:bg-purple-600"
                >
                  <Building2 className="w-4 h-4" />
                  View Demo
                  <ArrowRight className="w-4 h-4" />
                </a>
              </div>
            </div>
          </div>

          <div className="flex items-center justify-center gap-6 text-sm text-zinc-500">
            <div className="flex items-center gap-1.5">
              <Shield className="w-4 h-4" />
              <span>Read-only access</span>
            </div>
            <div className="flex items-center gap-1.5">
              <CheckCircle className="w-4 h-4" />
              <span>Privacy-first</span>
            </div>
          </div>
        </div>

        {/* Features */}
        <div className="grid md:grid-cols-3 gap-6 mb-20">
          <div className="card">
            <div className="w-10 h-10 rounded-lg bg-zinc-800 flex items-center justify-center mb-4">
              <Mail className="w-5 h-5 text-zinc-400" />
            </div>
            <h3 className="text-lg font-medium text-zinc-100 mb-2">
              Auto-Discovery
            </h3>
            <p className="text-zinc-400 text-sm">
              We scan your email for receipts and invoices to find all your
              active subscriptions automatically.
            </p>
          </div>

          <div className="card">
            <div className="w-10 h-10 rounded-lg bg-zinc-800 flex items-center justify-center mb-4">
              <TrendingDown className="w-5 h-5 text-zinc-400" />
            </div>
            <h3 className="text-lg font-medium text-zinc-100 mb-2">
              Smart Recommendations
            </h3>
            <p className="text-zinc-400 text-sm">
              Our AI analyzes your usage patterns and suggests which
              subscriptions to cancel or review.
            </p>
          </div>

          <div className="card">
            <div className="w-10 h-10 rounded-lg bg-zinc-800 flex items-center justify-center mb-4">
              <DollarSign className="w-5 h-5 text-zinc-400" />
            </div>
            <h3 className="text-lg font-medium text-zinc-100 mb-2">
              Save Money
            </h3>
            <p className="text-zinc-400 text-sm">
              Cancel unused subscriptions and track your recurring
              expenses to maximize savings.
            </p>
          </div>
        </div>

        {/* How it works */}
        <div className="card mb-20">
          <h2 className="text-xl font-medium text-zinc-100 text-center mb-8">
            How it works
          </h2>
          <div className="grid md:grid-cols-4 gap-6">
            {[
              { step: 1, title: "Connect Gmail", desc: "Securely connect your Google account" },
              { step: 2, title: "We scan emails", desc: "Find receipts and invoices automatically" },
              { step: 3, title: "Review suggestions", desc: "See which subscriptions to cancel" },
              { step: 4, title: "Take action", desc: "Accept or reject recommendations" },
            ].map((item) => (
              <div key={item.step} className="text-center">
                <div className="w-10 h-10 rounded-lg bg-zinc-800 text-zinc-400 font-medium flex items-center justify-center mx-auto mb-3">
                  {item.step}
                </div>
                <h4 className="font-medium text-zinc-100 mb-1">{item.title}</h4>
                <p className="text-sm text-zinc-500">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Privacy */}
        <div className="card text-center mb-12">
          <div className="w-10 h-10 rounded-lg bg-zinc-800 flex items-center justify-center mx-auto mb-4">
            <Shield className="w-5 h-5 text-zinc-400" />
          </div>
          <h3 className="text-xl font-medium text-zinc-100 mb-3">
            Your privacy is protected
          </h3>
          <p className="text-zinc-400 max-w-xl mx-auto text-sm">
            We only request read-only access to your Gmail. We scan for receipts
            and invoices but never read your personal messages. Your data is
            encrypted and never shared with third parties.
          </p>
        </div>
      </div>

      {/* Footer */}
      <footer className="border-t border-zinc-800 py-6">
        <div className="max-w-5xl mx-auto px-6 text-center text-zinc-500 text-sm">
          <p>&copy; 2024 Sub-Zero. All rights reserved.</p>
        </div>
      </footer>
    </div>
  );
}
