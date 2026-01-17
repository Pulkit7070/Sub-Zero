"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Snowflake, Mail, DollarSign, TrendingDown, CheckCircle, Zap, Shield, ArrowRight } from "lucide-react";
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
        <div className="w-12 h-12 rounded-full border-2 border-sky-500/30 border-t-sky-500 animate-spin"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen relative overflow-hidden">
      {/* Animated background orbs */}
      <div className="orb w-96 h-96 bg-sky-500/20 -top-48 -left-48" style={{ animationDelay: '0s' }}></div>
      <div className="orb w-80 h-80 bg-indigo-500/20 top-1/3 -right-40" style={{ animationDelay: '2s' }}></div>
      <div className="orb w-64 h-64 bg-emerald-500/10 bottom-20 left-1/4" style={{ animationDelay: '4s' }}></div>

      <div className="max-w-6xl mx-auto px-4 py-8 relative z-10">
        {/* Header */}
        <header className="flex items-center justify-between mb-20">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-sky-400 to-indigo-500 flex items-center justify-center">
              <Snowflake className="w-6 h-6 text-white" />
            </div>
            <span className="text-2xl font-bold text-white">Sub-Zero</span>
          </div>
        </header>

        {/* Hero */}
        <div className="text-center max-w-4xl mx-auto mb-24">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-white/5 border border-white/10 mb-8">
            <Zap className="w-4 h-4 text-amber-400" />
            <span className="text-sm text-slate-300">AI-powered subscription management</span>
          </div>
          
          <h1 className="text-5xl md:text-7xl font-bold mb-6 leading-tight">
            <span className="text-white">Take control of your</span>
            <br />
            <span className="gradient-text">subscriptions</span>
          </h1>
          
          <p className="text-xl text-slate-400 mb-10 max-w-2xl mx-auto leading-relaxed">
            Connect your Gmail to automatically discover all your subscriptions.
            Get smart recommendations and save money on services you don&apos;t use.
          </p>
          
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <a
              href={api.getLoginUrl()}
              className="btn-primary inline-flex items-center gap-3 text-lg px-8 py-4"
            >
              <Mail className="w-5 h-5" />
              Connect Gmail to Get Started
              <ArrowRight className="w-5 h-5" />
            </a>
          </div>
          
          <div className="flex items-center justify-center gap-6 mt-8 text-sm text-slate-500">
            <div className="flex items-center gap-2">
              <Shield className="w-4 h-4" />
              <span>Read-only access</span>
            </div>
            <div className="flex items-center gap-2">
              <CheckCircle className="w-4 h-4" />
              <span>Privacy-first</span>
            </div>
          </div>
        </div>

        {/* Features */}
        <div className="grid md:grid-cols-3 gap-6 mb-24">
          <div className="glass-card group hover:scale-[1.02] transition-transform duration-300">
            <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-sky-500/20 to-sky-500/5 flex items-center justify-center mb-5 group-hover:scale-110 transition-transform">
              <Mail className="w-7 h-7 text-sky-400" />
            </div>
            <h3 className="text-xl font-semibold text-white mb-3">
              Auto-Discovery
            </h3>
            <p className="text-slate-400 leading-relaxed">
              We scan your email for receipts and invoices to find all your
              active subscriptions automatically.
            </p>
          </div>

          <div className="glass-card group hover:scale-[1.02] transition-transform duration-300">
            <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-emerald-500/20 to-emerald-500/5 flex items-center justify-center mb-5 group-hover:scale-110 transition-transform">
              <TrendingDown className="w-7 h-7 text-emerald-400" />
            </div>
            <h3 className="text-xl font-semibold text-white mb-3">
              Smart Recommendations
            </h3>
            <p className="text-slate-400 leading-relaxed">
              Our AI analyzes your usage patterns and suggests which
              subscriptions to cancel or review.
            </p>
          </div>

          <div className="glass-card group hover:scale-[1.02] transition-transform duration-300">
            <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-amber-500/20 to-amber-500/5 flex items-center justify-center mb-5 group-hover:scale-110 transition-transform">
              <DollarSign className="w-7 h-7 text-amber-400" />
            </div>
            <h3 className="text-xl font-semibold text-white mb-3">
              Save Money
            </h3>
            <p className="text-slate-400 leading-relaxed">
              Cancel unused subscriptions and track your recurring
              expenses to maximize savings.
            </p>
          </div>
        </div>

        {/* How it works */}
        <div className="glass-card mb-24">
          <h2 className="text-2xl font-bold text-white text-center mb-10">
            How it works
          </h2>
          <div className="grid md:grid-cols-4 gap-8">
            {[
              { step: 1, title: "Connect Gmail", desc: "Securely connect your Google account", color: "sky" },
              { step: 2, title: "We scan emails", desc: "Find receipts and invoices automatically", color: "indigo" },
              { step: 3, title: "Review suggestions", desc: "See which subscriptions to cancel", color: "emerald" },
              { step: 4, title: "Take action", desc: "Accept or reject recommendations", color: "amber" },
            ].map((item) => (
              <div key={item.step} className="text-center group">
                <div className={`w-12 h-12 rounded-2xl bg-${item.color}-500/20 text-${item.color}-400 font-bold text-lg flex items-center justify-center mx-auto mb-4 group-hover:scale-110 transition-transform`}>
                  {item.step}
                </div>
                <h4 className="font-semibold text-white mb-2">{item.title}</h4>
                <p className="text-sm text-slate-400">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Privacy */}
        <div className="gradient-card text-center mb-16">
          <div className="w-16 h-16 rounded-2xl bg-emerald-500/20 flex items-center justify-center mx-auto mb-6">
            <Shield className="w-8 h-8 text-emerald-400" />
          </div>
          <h3 className="text-2xl font-semibold text-white mb-4">
            Your privacy is protected
          </h3>
          <p className="text-slate-400 max-w-2xl mx-auto leading-relaxed">
            We only request read-only access to your Gmail. We scan for receipts
            and invoices but never read your personal messages. Your data is
            encrypted and never shared with third parties.
          </p>
        </div>
      </div>

      {/* Footer */}
      <footer className="border-t border-white/5 py-8">
        <div className="max-w-6xl mx-auto px-4 text-center text-slate-500 text-sm">
          <p>&copy; 2024 Sub-Zero. All rights reserved.</p>
        </div>
      </footer>
    </div>
  );
}
