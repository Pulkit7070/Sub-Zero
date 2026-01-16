"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Snowflake, Mail, DollarSign, TrendingDown, CheckCircle } from "lucide-react";
import { api } from "@/lib/api";

export default function LandingPage() {
  const router = useRouter();
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    // Check if user is already logged in
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
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      {/* Hero Section */}
      <div className="max-w-6xl mx-auto px-4 py-16">
        {/* Header */}
        <header className="flex items-center justify-between mb-16">
          <div className="flex items-center gap-2">
            <Snowflake className="w-8 h-8 text-primary-600" />
            <span className="text-2xl font-bold text-gray-900">Sub-Zero</span>
          </div>
        </header>

        {/* Hero */}
        <div className="text-center max-w-3xl mx-auto mb-16">
          <h1 className="text-5xl font-bold text-gray-900 mb-6">
            Take control of your
            <span className="text-primary-600"> subscriptions</span>
          </h1>
          <p className="text-xl text-gray-600 mb-8">
            Connect your Gmail to automatically find all your subscriptions.
            Get smart recommendations to save money on services you don&apos;t use.
          </p>
          <a
            href={api.getLoginUrl()}
            className="inline-flex items-center gap-3 bg-primary-600 text-white px-8 py-4 rounded-xl font-semibold text-lg hover:bg-primary-700 transition-colors shadow-lg shadow-primary-600/25"
          >
            <Mail className="w-6 h-6" />
            Connect Gmail to Get Started
          </a>
          <p className="text-sm text-gray-500 mt-4">
            We only read receipts and invoices. Your emails stay private.
          </p>
        </div>

        {/* Features */}
        <div className="grid md:grid-cols-3 gap-8 mb-16">
          <div className="card text-center">
            <div className="w-12 h-12 bg-primary-100 rounded-xl flex items-center justify-center mx-auto mb-4">
              <Mail className="w-6 h-6 text-primary-600" />
            </div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              Auto-Discovery
            </h3>
            <p className="text-gray-600">
              We scan your email for receipts and invoices to find all your
              active subscriptions automatically.
            </p>
          </div>

          <div className="card text-center">
            <div className="w-12 h-12 bg-green-100 rounded-xl flex items-center justify-center mx-auto mb-4">
              <TrendingDown className="w-6 h-6 text-green-600" />
            </div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              Smart Recommendations
            </h3>
            <p className="text-gray-600">
              Our engine analyzes your usage patterns and suggests which
              subscriptions to cancel or review.
            </p>
          </div>

          <div className="card text-center">
            <div className="w-12 h-12 bg-amber-100 rounded-xl flex items-center justify-center mx-auto mb-4">
              <DollarSign className="w-6 h-6 text-amber-600" />
            </div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              Save Money
            </h3>
            <p className="text-gray-600">
              Cancel unused subscriptions and keep track of your recurring
              expenses to maximize savings.
            </p>
          </div>
        </div>

        {/* How it works */}
        <div className="card mb-16">
          <h2 className="text-2xl font-bold text-gray-900 text-center mb-8">
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
                <div className="w-10 h-10 rounded-full bg-primary-600 text-white font-bold flex items-center justify-center mx-auto mb-3">
                  {item.step}
                </div>
                <h4 className="font-semibold text-gray-900 mb-1">{item.title}</h4>
                <p className="text-sm text-gray-600">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Privacy */}
        <div className="bg-gray-50 rounded-2xl p-8 text-center">
          <CheckCircle className="w-12 h-12 text-green-600 mx-auto mb-4" />
          <h3 className="text-xl font-semibold text-gray-900 mb-2">
            Your privacy is protected
          </h3>
          <p className="text-gray-600 max-w-2xl mx-auto">
            We only request read-only access to your Gmail. We scan for receipts
            and invoices but never read your personal messages. Your data is
            encrypted and never shared with third parties.
          </p>
        </div>
      </div>

      {/* Footer */}
      <footer className="border-t border-gray-200 py-8">
        <div className="max-w-6xl mx-auto px-4 text-center text-gray-500 text-sm">
          <p>&copy; 2024 Sub-Zero. All rights reserved.</p>
        </div>
      </footer>
    </div>
  );
}
