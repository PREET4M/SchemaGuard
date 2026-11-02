"use client";

import { useEffect, useState, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  ShieldCheck,
  AlertTriangle,
  AlertOctagon,
  CheckCircle2,
  Clock,
  Download,
  RotateCcw,
  ArrowLeft,
  Database,
  Code2,
  FileText,
  Activity,
  Layers,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { RehearsalReport } from "@/types/schemaguard";

function ResultsContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const rehearsalId = searchParams.get("id");

  const [report, setReport] = useState<RehearsalReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<
    "overview" | "diff" | "contracts" | "invariants" | "profiler" | "warnings"
  >("overview");

  useEffect(() => {
    async function loadReport() {
      // Check session storage first
      const cached = sessionStorage.getItem("latest_rehearsal_report");
      if (cached) {
        try {
          const parsed: RehearsalReport = JSON.parse(cached);
          if (!rehearsalId || parsed.rehearsal_id === rehearsalId) {
            setReport(parsed);
            setLoading(false);
            return;
          }
        } catch {
          // ignore cache parse error
        }
      }

      if (rehearsalId) {
        try {
          setLoading(true);
          const res = await fetch(`/api/rehearsals/${rehearsalId}`);
          if (res.ok) {
            const data: RehearsalReport = await res.json();
            setReport(data);
          } else {
            setError("Rehearsal report not found or expired. Please run a new rehearsal.");
          }
        } catch (err) {
          setError("Failed to retrieve rehearsal report.");
        } finally {
          setLoading(false);
        }
      } else {
        setLoading(false);
      }
    }
    loadReport();
  }, [rehearsalId]);

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-20 text-center">
        <div className="w-8 h-8 rounded-full border-2 border-[#2563EB] border-t-transparent animate-spin mx-auto mb-4" />
        <p className="text-sm font-medium text-[#647084]">Loading rehearsal evidence...</p>
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className="max-w-2xl mx-auto px-4 py-20 text-center">
        <div className="w-12 h-12 rounded-xl bg-[#F1F4F8] text-[#647084] flex items-center justify-center mx-auto mb-4">
          <FileText className="w-6 h-6" />
        </div>
        <h2 className="text-xl font-bold text-[#171C26] mb-2">No Active Rehearsal Report</h2>
        <p className="text-sm text-[#647084] mb-6">
          {error || "Execute a migration in the Rehearsal Workspace or launch an instant demo scenario."}
        </p>
        <div className="flex items-center justify-center gap-4">
          <Link
            href="/rehearsal"
            className="px-5 py-2.5 text-sm font-semibold text-white bg-[#2563EB] hover:bg-[#1D4ED8] rounded-lg transition-colors"
          >
            Go to Rehearsal
          </Link>
          <Link
            href="/"
            className="px-5 py-2.5 text-sm font-semibold text-[#171C26] bg-[#FFFFFF] border border-[#E5E9F0] hover:bg-[#F1F4F8] rounded-lg transition-colors"
          >
            Return Home
          </Link>
        </div>
      </div>
    );
  }

  const { severity, label, succeeded, migration_result, risk_assessment, schema_diff, contract_results, invariant_results, data_profile, schema_findings } = report;

  // Severity semantic badge colors
  const getSeverityBadge = () => {
    switch (severity) {
      case "CRITICAL":
        return {
          bg: "bg-[#DC4B4B]/10",
          border: "border-[#DC4B4B]/30",
          text: "text-[#DC4B4B]",
          icon: AlertOctagon,
        };
      case "HIGH":
        return {
          bg: "bg-[#D99A22]/10",
          border: "border-[#D99A22]/30",
          text: "text-[#D99A22]",
          icon: AlertTriangle,
        };
      case "MODERATE":
        return {
          bg: "bg-[#D99A22]/10",
          border: "border-[#D99A22]/30",
          text: "text-[#D99A22]",
          icon: AlertTriangle,
        };
      case "LOW":
      default:
        return {
          bg: "bg-[#159B67]/10",
          border: "border-[#159B67]/30",
          text: "text-[#159B67]",
          icon: CheckCircle2,
        };
    }
  };

  const badgeTheme = getSeverityBadge();
  const BadgeIcon = badgeTheme.icon;

  const passedContracts = contract_results.filter((c) => c.status === "PASS").length;
  const passedInvariants = invariant_results.filter((i) => i.held).length;
  const totalTablesChanged = schema_diff.tables_added.length + schema_diff.tables_removed.length + schema_diff.tables_modified.length;

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      {/* Top Back Action */}
      <div className="mb-6 flex items-center justify-between">
        <Link
          href="/rehearsal"
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-[#647084] hover:text-[#171C26] transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Back to Configuration</span>
        </Link>
        <span className="text-xs font-mono text-[#929BA9]" suppressHydrationWarning>
          ID: {report.rehearsal_id.slice(0, 8)} • {new Date(report.timestamp).toLocaleTimeString()}
        </span>
      </div>

      {/* Results Header: Verdict Card */}
      <div className="bg-[#FFFFFF] border border-[#E5E9F0] rounded-2xl p-6 sm:p-8 mb-8 shadow-sm">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 pb-6 border-b border-[#E5E9F0]">
          <div>
            <div className="text-xs font-bold uppercase tracking-wider text-[#929BA9] mb-2">
              Rehearsal Verdict
            </div>
            <div className="flex items-center gap-3">
              <span
                className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-lg text-sm font-bold border ${badgeTheme.bg} ${badgeTheme.border} ${badgeTheme.text}`}
              >
                <BadgeIcon className="w-4 h-4" />
                <span>{severity}</span>
              </span>
              <h1 className="text-2xl font-extrabold text-[#171C26]">
                {label}
              </h1>
            </div>
            <p className="mt-2 text-xs sm:text-sm text-[#647084] max-w-2xl leading-relaxed">
              Executed against an isolated temporary clone. Source database remained in read-only mode with zero mutations.
            </p>
          </div>

          {/* Migration Execution Status */}
          <div className="bg-[#F7F8FA] p-4 rounded-xl border border-[#E5E9F0] min-w-[220px]">
            <div className="text-[11px] font-bold uppercase tracking-wider text-[#929BA9] mb-1">
              Sandbox DDL Status
            </div>
            <div className="text-sm font-bold text-[#171C26] flex items-center gap-1.5">
              <span className={`w-2 h-2 rounded-full ${migration_result.migration_applied ? "bg-[#159B67]" : "bg-[#DC4B4B]"}`} />
              <span>{migration_result.migration_applied ? "Applied Cleanly" : "Execution Failed"}</span>
            </div>
            <div className="mt-2 pt-2 border-t border-[#E5E9F0] text-xs font-mono text-[#647084] flex justify-between">
              <span>Time:</span>
              <strong className="text-[#171C26]">{migration_result.elapsed_total_ms} ms</strong>
            </div>
          </div>
        </div>

        {/* Compact Metrics Row */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 pt-6">
          <div className="bg-[#F7F8FA] p-4 rounded-xl border border-[#E5E9F0]">
            <span className="text-[11px] font-bold uppercase tracking-wider text-[#929BA9] block mb-1">
              Contracts Replayed
            </span>
            <div className="text-xl font-bold font-mono text-[#171C26]">
              {passedContracts} / {contract_results.length}
            </div>
            <span className="text-[11px] text-[#647084]">OLD_APP & NEW_APP</span>
          </div>

          <div className="bg-[#F7F8FA] p-4 rounded-xl border border-[#E5E9F0]">
            <span className="text-[11px] font-bold uppercase tracking-wider text-[#929BA9] block mb-1">
              Invariants Held
            </span>
            <div className="text-xl font-bold font-mono text-[#171C26]">
              {passedInvariants} / {invariant_results.length}
            </div>
            <span className="text-[11px] text-[#647084]">0 violating rows</span>
          </div>

          <div className="bg-[#F7F8FA] p-4 rounded-xl border border-[#E5E9F0]">
            <span className="text-[11px] font-bold uppercase tracking-wider text-[#929BA9] block mb-1">
              Tables Changed
            </span>
            <div className="text-xl font-bold font-mono text-[#171C26]">
              {totalTablesChanged}
            </div>
            <span className="text-[11px] text-[#647084]">+{schema_diff.tables_added.length} / -{schema_diff.tables_removed.length}</span>
          </div>

          <div className="bg-[#F7F8FA] p-4 rounded-xl border border-[#E5E9F0]">
            <span className="text-[11px] font-bold uppercase tracking-wider text-[#929BA9] block mb-1">
              Static Warnings
            </span>
            <div className="text-xl font-bold font-mono text-[#171C26]">
              {schema_findings.length}
            </div>
            <span className="text-[11px] text-[#647084]">SQLGlot AST checks</span>
          </div>
        </div>
      </div>

      {/* Results Navigation Tabs */}
      <div className="border-b border-[#E5E9F0] mb-6 flex overflow-x-auto gap-2">
        <button
          onClick={() => setActiveTab("overview")}
          className={`px-4 py-2.5 text-xs font-bold uppercase tracking-wider border-b-2 transition-colors cursor-pointer whitespace-nowrap ${
            activeTab === "overview"
              ? "border-[#2563EB] text-[#2563EB]"
              : "border-transparent text-[#647084] hover:text-[#171C26]"
          }`}
        >
          Overview
        </button>
        <button
          onClick={() => setActiveTab("diff")}
          className={`px-4 py-2.5 text-xs font-bold uppercase tracking-wider border-b-2 transition-colors cursor-pointer whitespace-nowrap ${
            activeTab === "diff"
              ? "border-[#2563EB] text-[#2563EB]"
              : "border-transparent text-[#647084] hover:text-[#171C26]"
          }`}
        >
          Schema Diff ({totalTablesChanged})
        </button>
        <button
          onClick={() => setActiveTab("contracts")}
          className={`px-4 py-2.5 text-xs font-bold uppercase tracking-wider border-b-2 transition-colors cursor-pointer whitespace-nowrap ${
            activeTab === "contracts"
              ? "border-[#2563EB] text-[#2563EB]"
              : "border-transparent text-[#647084] hover:text-[#171C26]"
          }`}
        >
          Contracts ({contract_results.length})
        </button>
        <button
          onClick={() => setActiveTab("invariants")}
          className={`px-4 py-2.5 text-xs font-bold uppercase tracking-wider border-b-2 transition-colors cursor-pointer whitespace-nowrap ${
            activeTab === "invariants"
              ? "border-[#2563EB] text-[#2563EB]"
              : "border-transparent text-[#647084] hover:text-[#171C26]"
          }`}
        >
          Invariants ({invariant_results.length})
        </button>
        <button
          onClick={() => setActiveTab("profiler")}
          className={`px-4 py-2.5 text-xs font-bold uppercase tracking-wider border-b-2 transition-colors cursor-pointer whitespace-nowrap ${
            activeTab === "profiler"
              ? "border-[#2563EB] text-[#2563EB]"
              : "border-transparent text-[#647084] hover:text-[#171C26]"
          }`}
        >
          Row Profiler ({data_profile.length})
        </button>
        <button
          onClick={() => setActiveTab("warnings")}
          className={`px-4 py-2.5 text-xs font-bold uppercase tracking-wider border-b-2 transition-colors cursor-pointer whitespace-nowrap ${
            activeTab === "warnings"
              ? "border-[#2563EB] text-[#2563EB]"
              : "border-transparent text-[#647084] hover:text-[#171C26]"
          }`}
        >
          Static Warnings ({schema_findings.length})
        </button>
      </div>

      {/* TAB CONTENT */}

      {/* 1. OVERVIEW */}
      {activeTab === "overview" && (
        <div className="space-y-6">
          <div className="bg-[#FFFFFF] border border-[#E5E9F0] rounded-xl p-6 shadow-sm">
            <h3 className="text-base font-bold text-[#171C26] mb-3">
              Executive Rehearsal Summary
            </h3>
            <p className="text-sm text-[#647084] leading-relaxed mb-4">
              {succeeded
                ? "All configured contracts, invariants, and migration statements passed cleanly in the temporary sandbox clone with zero detected regressions."
                : "One or more verification checks failed. Review the detailed tabs below before proceeding with deployment."}
            </p>

            {/* Precedence Principle Callout */}
            {severity === "CRITICAL" && (
              <div className="p-4 bg-[#DC4B4B]/10 border border-[#DC4B4B]/30 rounded-lg text-xs text-[#DC4B4B] mb-4">
                <strong>Precedence Principle:</strong> An active application contract failed or the migration DDL threw an error. Functional breakage strictly triggers a CRITICAL rating regardless of numeric scoring.
              </div>
            )}

            {/* Heuristic Score Breakdown */}
            <div className="bg-[#F7F8FA] p-4 rounded-xl border border-[#E5E9F0]">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-bold uppercase tracking-wider text-[#929BA9]">
                  Secondary Heuristic Risk Score
                </span>
                <span className="text-sm font-bold font-mono text-[#171C26]">
                  {risk_assessment.risk_score} / 100
                </span>
              </div>
              <div className="w-full bg-[#E5E9F0] h-2 rounded-full overflow-hidden">
                <div
                  className={`h-full ${
                    risk_assessment.risk_score > 50
                      ? "bg-[#DC4B4B]"
                      : risk_assessment.risk_score > 20
                      ? "bg-[#D99A22]"
                      : "bg-[#159B67]"
                  }`}
                  style={{ width: `${Math.min(risk_assessment.risk_score, 100)}%` }}
                />
              </div>

              {risk_assessment.factors && risk_assessment.factors.length > 0 && (
                <div className="mt-4 pt-3 border-t border-[#E5E9F0] space-y-1.5">
                  <span className="text-[11px] font-bold text-[#929BA9] uppercase tracking-wider block">
                    Contributing Risk Factors:
                  </span>
                  {risk_assessment.factors.map((f, i) => (
                    <div key={i} className="text-xs text-[#647084] flex items-center justify-between">
                      <span>• {f.description}</span>
                      <strong className="text-[#DC4B4B]">+{f.points} pts</strong>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Rehearsed Migration SQL View */}
          <div className="bg-[#FFFFFF] border border-[#E5E9F0] rounded-xl p-6 shadow-sm">
            <h4 className="text-sm font-bold text-[#171C26] mb-2">
              Rehearsed Migration SQL
            </h4>
            <div className="p-4 light-code-editor text-xs font-mono rounded-lg overflow-x-auto">
              <pre>{migration_result.migration_sql}</pre>
            </div>
          </div>
        </div>
      )}

      {/* 2. SCHEMA DIFF */}
      {activeTab === "diff" && (
        <div className="bg-[#FFFFFF] border border-[#E5E9F0] rounded-xl p-6 shadow-sm space-y-6">
          <h3 className="text-base font-bold text-[#171C26] mb-1">
            Structural Schema Diff
          </h3>
          <p className="text-xs text-[#647084] mb-4">
            Comparison between baseline pre-migration schema and post-migration sandbox database.
          </p>

          {schema_diff.is_clean ? (
            <div className="p-4 bg-[#159B67]/10 border border-[#159B67]/25 rounded-lg text-xs text-[#159B67]">
              ✓ No structural schema changes detected.
            </div>
          ) : (
            <div className="space-y-4 text-xs font-mono">
              {schema_diff.tables_added.map((t) => (
                <div key={t} className="p-3 bg-[#159B67]/10 border border-[#159B67]/25 rounded-lg text-[#159B67]">
                  + ADD TABLE <strong>{t}</strong>
                </div>
              ))}
              {schema_diff.tables_removed.map((t) => (
                <div key={t} className="p-3 bg-[#DC4B4B]/10 border border-[#DC4B4B]/25 rounded-lg text-[#DC4B4B]">
                  - DROP TABLE <strong>{t}</strong>
                </div>
              ))}
              {Object.entries(schema_diff.columns_added).map(([tbl, cols]) =>
                cols.map((col) => (
                  <div key={`${tbl}.${col}`} className="p-3 bg-[#159B67]/10 border border-[#159B67]/25 rounded-lg text-[#159B67]">
                    + ADD COLUMN <strong>{tbl}.{col}</strong>
                  </div>
                ))
              )}
              {Object.entries(schema_diff.columns_removed).map(([tbl, cols]) =>
                cols.map((col) => (
                  <div key={`${tbl}.${col}`} className="p-3 bg-[#DC4B4B]/10 border border-[#DC4B4B]/25 rounded-lg text-[#DC4B4B]">
                    - DROP COLUMN <strong>{tbl}.{col}</strong>
                  </div>
                ))
              )}
              {Object.entries(schema_diff.columns_modified).map(([tbl, cols]) =>
                Object.entries(cols).map(([col, [oldT, newT]]) => (
                  <div key={`${tbl}.${col}`} className="p-3 bg-[#D99A22]/10 border border-[#D99A22]/25 rounded-lg text-[#D99A22]">
                    ~ MODIFY COLUMN <strong>{tbl}.{col}</strong> ({oldT} → {newT})
                  </div>
                ))
              )}
            </div>
          )}
        </div>
      )}

      {/* 3. APPLICATION CONTRACTS */}
      {activeTab === "contracts" && (
        <div className="space-y-4">
          {contract_results.length === 0 ? (
            <div className="p-8 text-center bg-[#FFFFFF] border border-[#E5E9F0] rounded-xl text-xs text-[#647084]">
              No application contracts were configured for this run.
            </div>
          ) : (
            contract_results.map((c, i) => (
              <div key={i} className="bg-[#FFFFFF] border border-[#E5E9F0] rounded-xl p-5 shadow-sm">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-bold text-[#171C26]">{c.name}</span>
                    <span className="text-[11px] font-semibold text-[#647084] bg-[#F1F4F8] px-2 py-0.5 rounded">
                      {c.contract_type}
                    </span>
                  </div>
                  <span
                    className={`text-xs font-bold px-2.5 py-0.5 rounded border ${
                      c.status === "PASS"
                        ? "bg-[#159B67]/10 text-[#159B67] border-[#159B67]/20"
                        : "bg-[#DC4B4B]/10 text-[#DC4B4B] border-[#DC4B4B]/20"
                    }`}
                  >
                    {c.status}
                  </span>
                </div>
                <div className="p-3 light-code-editor text-xs font-mono rounded-lg mb-2">
                  <pre>{c.sql_statement}</pre>
                </div>
                {c.error_message ? (
                  <div className="p-3 bg-[#DC4B4B]/10 border border-[#DC4B4B]/25 rounded-lg text-xs text-[#DC4B4B]">
                    Error: {c.error_message}
                  </div>
                ) : (
                  <div className="text-xs text-[#647084]">
                    Returned <strong>{c.row_count_post} row(s)</strong> in {c.execution_time_ms} ms. Columns: {c.column_names.join(", ") || "none"}
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      )}

      {/* 4. BUSINESS INVARIANTS */}
      {activeTab === "invariants" && (
        <div className="space-y-4">
          {invariant_results.length === 0 ? (
            <div className="p-8 text-center bg-[#FFFFFF] border border-[#E5E9F0] rounded-xl text-xs text-[#647084]">
              No business invariants were configured for this run.
            </div>
          ) : (
            invariant_results.map((inv, i) => (
              <div key={i} className="bg-[#FFFFFF] border border-[#E5E9F0] rounded-xl p-5 shadow-sm">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-bold text-[#171C26]">{inv.name}</span>
                  <span
                    className={`text-xs font-bold px-2.5 py-0.5 rounded border ${
                      inv.held
                        ? "bg-[#159B67]/10 text-[#159B67] border-[#159B67]/20"
                        : "bg-[#DC4B4B]/10 text-[#DC4B4B] border-[#DC4B4B]/20"
                    }`}
                  >
                    {inv.held ? "PASS (0 Rows)" : `FAIL (${inv.violating_rows_count} Rows)`}
                  </span>
                </div>
                <div className="p-3 light-code-editor text-xs font-mono rounded-lg mb-2">
                  <pre>{inv.sql}</pre>
                </div>
                {inv.error_message ? (
                  <div className="p-3 bg-[#DC4B4B]/10 border border-[#DC4B4B]/25 rounded-lg text-xs text-[#DC4B4B]">
                    Error: {inv.error_message}
                  </div>
                ) : (
                  <div className="text-xs text-[#647084]">
                    {inv.held ? (
                      <span className="text-[#159B67] font-semibold">✓ Invariant held: 0 violating rows returned ({inv.execution_time_ms} ms).</span>
                    ) : (
                      <span className="text-[#DC4B4B] font-semibold">⚠️ Invariant violated: {inv.violating_rows_count} row(s) returned!</span>
                    )}
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      )}

      {/* 5. PROFILER */}
      {activeTab === "profiler" && (
        <div className="bg-[#FFFFFF] border border-[#E5E9F0] rounded-xl p-6 shadow-sm overflow-x-auto">
          <h3 className="text-base font-bold text-[#171C26] mb-1">
            Table Row Count Tracking
          </h3>
          <p className="text-xs text-[#647084] mb-4">
            Tracks baseline row counts against post-migration counts to catch accidental bulk drops.
          </p>
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-[#E5E9F0] text-[#929BA9] uppercase font-bold">
                <th className="py-2.5">Table</th>
                <th className="py-2.5">Pre-Migration</th>
                <th className="py-2.5">Post-Migration</th>
                <th className="py-2.5">Delta</th>
                <th className="py-2.5">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#E5E9F0]">
              {data_profile.map((tp) => (
                <tr key={tp.table_name}>
                  <td className="py-2.5 font-mono font-bold text-[#171C26]">{tp.table_name}</td>
                  <td className="py-2.5 font-mono text-[#647084]">{tp.pre_count}</td>
                  <td className="py-2.5 font-mono text-[#171C26]">{tp.post_count}</td>
                  <td className="py-2.5 font-mono">
                    {tp.delta !== null ? (
                      <span className={tp.delta < 0 ? "text-[#DC4B4B] font-bold" : "text-[#159B67]"}>
                        {tp.delta > 0 ? `+${tp.delta}` : tp.delta}
                      </span>
                    ) : (
                      "N/A"
                    )}
                  </td>
                  <td className="py-2.5">
                    {tp.is_row_drop || tp.status === "dropped" ? (
                      <span className="text-[11px] font-bold text-[#DC4B4B] bg-[#DC4B4B]/10 px-2 py-0.5 rounded">
                        ⚠️ DROP ANOMALY
                      </span>
                    ) : (
                      <span className="text-[11px] font-bold text-[#159B67] bg-[#159B67]/10 px-2 py-0.5 rounded">
                        ✓ UNTOUCHED
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* 6. STATIC WARNINGS */}
      {activeTab === "warnings" && (
        <div className="space-y-4">
          {schema_findings.length === 0 ? (
            <div className="p-8 text-center bg-[#FFFFFF] border border-[#E5E9F0] rounded-xl text-xs text-[#159B67]">
              ✓ No static SQL warnings detected by SQLGlot AST analysis.
            </div>
          ) : (
            schema_findings.map((f, i) => (
              <div key={i} className="bg-[#FFFFFF] border border-[#E5E9F0] rounded-xl p-5 shadow-sm">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold text-[#DC4B4B] bg-[#DC4B4B]/10 border border-[#DC4B4B]/20 px-2 py-0.5 rounded">
                      {f.severity}
                    </span>
                    <span className="text-sm font-bold text-[#171C26]">{f.title}</span>
                    <span className="text-xs font-mono text-[#929BA9]">[{f.rule_id}]</span>
                  </div>
                </div>
                <p className="text-xs text-[#647084] mb-2">{f.explanation}</p>
                {f.evidence && (
                  <div className="p-2.5 light-code-editor text-xs font-mono rounded-lg mb-2">
                    <pre>{f.evidence}</pre>
                  </div>
                )}
                {f.human_review_action && (
                  <div className="text-xs text-[#0891B2]">
                    👉 <strong>Action:</strong> {f.human_review_action}
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      )}

      {/* Action Bar: Downloads & Navigation */}
      <div className="mt-10 pt-6 border-t border-[#E5E9F0] flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="flex items-center gap-3 w-full sm:w-auto">
          <a
            href={`/api/rehearsals/${report.rehearsal_id}/markdown`}
            download
            className="inline-flex items-center justify-center gap-1.5 px-4 py-2.5 text-xs font-bold text-[#171C26] bg-[#FFFFFF] hover:bg-[#F1F4F8] border border-[#E5E9F0] rounded-lg shadow-sm transition-colors"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Download Markdown</span>
          </a>
          <a
            href={`/api/rehearsals/${report.rehearsal_id}/json`}
            download
            className="inline-flex items-center justify-center gap-1.5 px-4 py-2.5 text-xs font-bold text-[#171C26] bg-[#FFFFFF] hover:bg-[#F1F4F8] border border-[#E5E9F0] rounded-lg shadow-sm transition-colors"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Download JSON</span>
          </a>
        </div>

        <div className="flex items-center gap-3 w-full sm:w-auto">
          <Link
            href="/rehearsal"
            className="inline-flex items-center justify-center gap-1.5 px-5 py-2.5 text-xs font-bold text-white bg-[#2563EB] hover:bg-[#1D4ED8] rounded-lg shadow-sm transition-colors"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>Run Another Rehearsal</span>
          </Link>
        </div>
      </div>
    </div>
  );
}

export default function ResultsPage() {
  return (
    <Suspense fallback={<div className="max-w-4xl mx-auto p-12 text-center text-sm text-[#647084]">Loading results...</div>}>
      <ResultsContent />
    </Suspense>
  );
}

