"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Shield, Lock, Settings as SettingsIcon, Terminal, CheckCircle2, ArrowLeft } from "lucide-react";
import { SystemSettings } from "@/types/schemaguard";

export default function SettingsPage() {
  const [settings, setSettings] = useState<SystemSettings | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchSettings() {
      try {
        const res = await fetch("/api/settings");
        if (res.ok) {
          const data: SystemSettings = await res.json();
          setSettings(data);
        }
      } catch (err) {
        console.error("Failed to load settings:", err);
      } finally {
        setLoading(false);
      }
    }
    fetchSettings();
  }, []);

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      <div className="mb-6">
        <Link
          href="/"
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-[#647084] hover:text-[#171C26] transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Back to Home</span>
        </Link>
      </div>

      <div className="mb-8">
        <h1 className="text-3xl font-extrabold text-[#171C26] tracking-tight">
          System Settings & Boundaries
        </h1>
        <p className="mt-2 text-sm text-[#647084]">
          Transparent inspection of execution constraints, connection PRAGMAs, security authorizer rules, and local runtime environment.
        </p>
      </div>

      <div className="space-y-6">
        {/* Execution Constraints */}
        <div className="bg-[#FFFFFF] border border-[#E5E9F0] rounded-xl p-6 shadow-sm">
          <h2 className="text-sm font-bold uppercase tracking-wider text-[#929BA9] mb-4 flex items-center gap-2">
            <Lock className="w-4 h-4 text-[#2563EB]" />
            <span>Execution Constraints</span>
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
            <div className="p-3 bg-[#F7F8FA] rounded-lg border border-[#E5E9F0] flex justify-between">
              <span className="text-[#647084]">Max Upload Size:</span>
              <strong className="text-[#171C26] font-mono">
                {settings?.constraints.max_upload_size_mb || 25} MB
              </strong>
            </div>
            <div className="p-3 bg-[#F7F8FA] rounded-lg border border-[#E5E9F0] flex justify-between">
              <span className="text-[#647084]">Statement Timeout:</span>
              <strong className="text-[#171C26] font-mono">
                {settings?.constraints.statement_timeout_seconds || 5.0} seconds
              </strong>
            </div>
            <div className="p-3 bg-[#F7F8FA] rounded-lg border border-[#E5E9F0] flex justify-between">
              <span className="text-[#647084]">Max Sample Rows:</span>
              <strong className="text-[#171C26] font-mono">
                {settings?.constraints.max_sample_rows || 100} rows
              </strong>
            </div>
            <div className="p-3 bg-[#F7F8FA] rounded-lg border border-[#E5E9F0] flex justify-between">
              <span className="text-[#647084]">Sandbox Clone File:</span>
              <strong className="text-[#2563EB] font-mono">
                {settings?.constraints.sandbox_clone_filename || "rehearsal_copy.db"}
              </strong>
            </div>
          </div>
        </div>

        {/* Security Authorizer Rules */}
        <div className="bg-[#FFFFFF] border border-[#E5E9F0] rounded-xl p-6 shadow-sm">
          <h2 className="text-sm font-bold uppercase tracking-wider text-[#929BA9] mb-4 flex items-center gap-2">
            <Shield className="w-4 h-4 text-[#159B67]" />
            <span>SQLite Authorizer Boundary</span>
          </h2>
          <p className="text-xs text-[#647084] mb-4">
            SQLite&apos;s low-level <code className="text-[#2563EB]">set_authorizer</code> callback strictly intercepts and blocks any actions attempting to escape the temporary sandbox:
          </p>
          <div className="space-y-2 text-xs">
            {settings?.authorizer_rules.map((rule, idx) => (
              <div
                key={idx}
                className="p-3 bg-[#F7F8FA] rounded-lg border border-[#E5E9F0] flex items-center gap-2.5 text-[#171C26]"
              >
                <CheckCircle2 className="w-4 h-4 text-[#159B67] shrink-0" />
                <span>{rule}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Connection Pragmas */}
        <div className="bg-[#FFFFFF] border border-[#E5E9F0] rounded-xl p-6 shadow-sm">
          <h2 className="text-sm font-bold uppercase tracking-wider text-[#929BA9] mb-4 flex items-center gap-2">
            <Terminal className="w-4 h-4 text-[#0891B2]" />
            <span>Sandbox Connection PRAGMAs</span>
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs font-mono">
            {settings &&
              Object.entries(settings.pragmas).map(([k, v]) => (
                <div
                  key={k}
                  className="p-2.5 bg-[#F7F8FA] rounded-lg border border-[#E5E9F0] flex justify-between"
                >
                  <span className="text-[#647084]">PRAGMA {k}</span>
                  <strong className="text-[#171C26]">{v}</strong>
                </div>
              ))}
          </div>
        </div>

        {/* Local Runtime Information */}
        <div className="bg-[#FFFFFF] border border-[#E5E9F0] rounded-xl p-6 shadow-sm">
          <h2 className="text-sm font-bold uppercase tracking-wider text-[#929BA9] mb-4 flex items-center gap-2">
            <SettingsIcon className="w-4 h-4 text-[#647084]" />
            <span>Local Runtime Environment</span>
          </h2>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs font-mono">
            <div className="p-3 bg-[#F7F8FA] rounded-lg border border-[#E5E9F0]">
              <span className="text-[#929BA9] block text-[10px] uppercase">Python</span>
              <strong className="text-[#171C26]">{settings?.runtime.python_version || "3.11"}</strong>
            </div>
            <div className="p-3 bg-[#F7F8FA] rounded-lg border border-[#E5E9F0]">
              <span className="text-[#929BA9] block text-[10px] uppercase">SQLite Engine</span>
              <strong className="text-[#171C26]">{settings?.runtime.sqlite_version || "3.45"}</strong>
            </div>
            <div className="p-3 bg-[#F7F8FA] rounded-lg border border-[#E5E9F0]">
              <span className="text-[#929BA9] block text-[10px] uppercase">SQLGlot Parser</span>
              <strong className="text-[#171C26]">{settings?.runtime.sqlglot_version || "25.0"}</strong>
            </div>
            <div className="p-3 bg-[#F7F8FA] rounded-lg border border-[#E5E9F0]">
              <span className="text-[#929BA9] block text-[10px] uppercase">Architecture</span>
              <strong className="text-[#171C26]">Local-First</strong>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
