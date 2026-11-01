"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import {
  ArrowRight,
  Database,
  Code2,
  CheckCircle2,
  FileText,
  Shield,
  Lock,
  Layers,
  Activity,
  AlertTriangle,
  Play,
} from "lucide-react";

export default function LandingPage() {
  const router = useRouter();

  const handleLaunchScenario = (scenarioKey: string) => {
    router.push(`/rehearsal?scenario=${scenarioKey}`);
  };

  return (
    <div className="relative overflow-hidden">
      {/* Background radial lighting */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full max-w-7xl h-[600px] pointer-events-none opacity-40">
        <div className="absolute top-[-150px] left-1/2 -translate-x-1/2 w-[700px] h-[450px] bg-gradient-to-b from-[#2563EB]/15 to-transparent blur-3xl rounded-full" />
      </div>

      {/* Hero Section */}
      <section className="relative pt-20 pb-16 md:pt-28 md:pb-24 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
        <motion.div
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: "easeOut" }}
          className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-lg bg-[#FFFFFF] border border-[#E5E9F0] text-xs font-semibold text-[#2563EB] shadow-sm mb-6"
        >
          <span className="w-2 h-2 rounded-full bg-[#159B67] animate-pulse" />
          <span>Local-First SQLite Migration Verification Engine</span>
        </motion.div>

        <motion.h1
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.1, ease: "easeOut" }}
          className="text-4xl sm:text-5xl md:text-6xl font-extrabold tracking-tight text-[#171C26] max-w-4xl mx-auto leading-[1.12]"
        >
          Validate database migrations before they reach production.
        </motion.h1>

        <motion.p
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.2, ease: "easeOut" }}
          className="mt-6 text-lg md:text-xl text-[#647084] max-w-2xl mx-auto leading-relaxed"
        >
          Rehearse schema changes against real application contracts in an isolated SQLite environment. Detect breaking changes before deployment.
        </motion.p>

        {/* Hero CTAs */}
        <motion.div
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.3, ease: "easeOut" }}
          className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4"
        >
          <Link
            href="/rehearsal"
            className="w-full sm:w-auto inline-flex items-center justify-center gap-2.5 px-6 py-3.5 text-base font-semibold text-white bg-[#2563EB] hover:bg-[#1D4ED8] active:bg-[#1E40AF] rounded-xl shadow-md hover:shadow-lg transition-all duration-150"
          >
            <span>Start Rehearsal</span>
            <ArrowRight className="w-4 h-4 stroke-[2.2]" />
          </Link>
          <a
            href="#how-it-works"
            className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-6 py-3.5 text-base font-semibold text-[#171C26] bg-[#FFFFFF] hover:bg-[#F1F4F8] border border-[#E5E9F0] rounded-xl shadow-sm transition-all duration-150"
          >
            <span>Explore How It Works</span>
          </a>
        </motion.div>

        {/* Trust Chips */}
        <div className="mt-12 flex flex-wrap items-center justify-center gap-6 text-xs font-medium text-[#647084]">
          <div className="flex items-center gap-1.5">
            <Lock className="w-3.5 h-3.5 text-[#159B67]" />
            <span>Zero Production Writes</span>
          </div>
          <div className="flex items-center gap-1.5">
            <Shield className="w-3.5 h-3.5 text-[#2563EB]" />
            <span>SQLite Backup API Clones</span>
          </div>
          <div className="flex items-center gap-1.5">
            <CheckCircle2 className="w-3.5 h-3.5 text-[#0891B2]" />
            <span>Deterministic Evidence Reports</span>
          </div>
        </div>
      </section>

      {/* Interactive Product Workflow Visualization */}
      <section id="product" className="py-12 md:py-16 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-10">
          <h2 className="text-xs font-bold uppercase tracking-wider text-[#2563EB] mb-2">
            Automated Rehearsal Pipeline
          </h2>
          <p className="text-2xl md:text-3xl font-bold text-[#171C26] tracking-tight">
            How SchemaGuard proves migration safety
          </p>
        </div>

        <div className="glass-panel p-6 sm:p-8 rounded-2xl relative overflow-hidden">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 relative z-10">
            {/* Step 1: Source Database */}
            <div className="bg-[#FFFFFF] border border-[#E5E9F0] p-5 rounded-xl hover:border-[#2563EB]/40 transition-all duration-200">
              <div className="w-10 h-10 rounded-lg bg-[#2563EB]/10 border border-[#2563EB]/20 flex items-center justify-center text-[#2563EB] mb-4">
                <Database className="w-5 h-5 stroke-[2]" />
              </div>
              <div className="text-xs font-bold uppercase tracking-wider text-[#929BA9] mb-1">
                Node 01
              </div>
              <h3 className="text-base font-bold text-[#171C26] mb-2">
                Source Database
              </h3>
              <p className="text-xs text-[#647084] leading-relaxed">
                Source opened strictly read-only (<code className="text-[#2563EB]">mode=ro</code>). Copied to an isolated temporary sandbox via native SQLite backup API.
              </p>
              <div className="mt-4 pt-3 border-t border-[#E5E9F0] text-[11px] font-semibold text-[#159B67] flex items-center gap-1">
                <span>✓ 0 Production Writes</span>
              </div>
            </div>

            {/* Step 2: Migration SQL */}
            <div className="bg-[#FFFFFF] border border-[#E5E9F0] p-5 rounded-xl hover:border-[#2563EB]/40 transition-all duration-200">
              <div className="w-10 h-10 rounded-lg bg-[#0891B2]/10 border border-[#0891B2]/20 flex items-center justify-center text-[#0891B2] mb-4">
                <Code2 className="w-5 h-5 stroke-[2]" />
              </div>
              <div className="text-xs font-bold uppercase tracking-wider text-[#929BA9] mb-1">
                Node 02
              </div>
              <h3 className="text-base font-bold text-[#171C26] mb-2">
                Migration DDL
              </h3>
              <p className="text-xs text-[#647084] leading-relaxed">
                Parsed via SQLGlot AST to catch unconstrained bulk deletes or dropped objects, then executed strictly on the isolated sandbox copy.
              </p>
              <div className="mt-4 pt-3 border-t border-[#E5E9F0] text-[11px] font-semibold text-[#2563EB] flex items-center gap-1">
                <span>✓ Transactional Sandbox</span>
              </div>
            </div>

            {/* Step 3: Validation */}
            <div className="bg-[#FFFFFF] border border-[#E5E9F0] p-5 rounded-xl hover:border-[#2563EB]/40 transition-all duration-200">
              <div className="w-10 h-10 rounded-lg bg-[#2563EB]/10 border border-[#2563EB]/20 flex items-center justify-center text-[#2563EB] mb-4">
                <Activity className="w-5 h-5 stroke-[2]" />
              </div>
              <div className="text-xs font-bold uppercase tracking-wider text-[#929BA9] mb-1">
                Node 03
              </div>
              <h3 className="text-base font-bold text-[#171C26] mb-2">
                Validation
              </h3>
              <p className="text-xs text-[#647084] leading-relaxed">
                Replays production contracts (<code className="text-[#2563EB]">OLD_APP</code> & <code className="text-[#2563EB]">NEW_APP</code>) and evaluates SQL domain invariants requiring 0 violating rows.
              </p>
              <div className="mt-4 pt-3 border-t border-[#E5E9F0] text-[11px] font-semibold text-[#0891B2] flex items-center gap-1">
                <span>✓ Authorizer Guarded</span>
              </div>
            </div>

            {/* Step 4: Result */}
            <div className="bg-[#FFFFFF] border border-[#E5E9F0] p-5 rounded-xl hover:border-[#2563EB]/40 transition-all duration-200">
              <div className="w-10 h-10 rounded-lg bg-[#159B67]/10 border border-[#159B67]/20 flex items-center justify-center text-[#159B67] mb-4">
                <FileText className="w-5 h-5 stroke-[2]" />
              </div>
              <div className="text-xs font-bold uppercase tracking-wider text-[#929BA9] mb-1">
                Node 04
              </div>
              <h3 className="text-base font-bold text-[#171C26] mb-2">
                Audit Evidence
              </h3>
              <p className="text-xs text-[#647084] leading-relaxed">
                Deterministic categorical severity (CRITICAL, HIGH, MODERATE, LOW: &quot;No configured checks failed&quot;) with PR-ready JSON and Markdown reports.
              </p>
              <div className="mt-4 pt-3 border-t border-[#E5E9F0] text-[11px] font-semibold text-[#159B67] flex items-center gap-1">
                <span>✓ Evidence Backed</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* How It Works Section */}
      <section id="how-it-works" className="py-16 md:py-24 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center max-w-2xl mx-auto mb-14">
          <h2 className="text-xs font-bold uppercase tracking-wider text-[#2563EB] mb-2">
            Workflow Overview
          </h2>
          <p className="text-3xl font-extrabold text-[#171C26] tracking-tight">
            Three simple steps to safe migrations
          </p>
          <p className="mt-3 text-sm text-[#647084]">
            Pre-flight verification designed to integrate directly into developer PR workflows.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {/* Card 01 */}
          <div className="card-elevated p-8 rounded-xl flex flex-col justify-between">
            <div>
              <div className="w-12 h-12 rounded-xl bg-[#F1F4F8] text-[#2563EB] font-bold text-lg flex items-center justify-center mb-6">
                01
              </div>
              <h3 className="text-xl font-bold text-[#171C26] mb-3">
                Select your database
              </h3>
              <p className="text-sm text-[#647084] leading-relaxed">
                Choose the synthetic eCommerce demo database or upload your own SQLite file. The engine validates database headers, table metadata, and inspects baseline row counts.
              </p>
            </div>
            <div className="mt-6 pt-4 border-t border-[#E5E9F0] text-xs font-medium text-[#929BA9]">
              Supports .db, .sqlite, and .sqlite3 up to 25 MB
            </div>
          </div>

          {/* Card 02 */}
          <div className="card-elevated p-8 rounded-xl flex flex-col justify-between">
            <div>
              <div className="w-12 h-12 rounded-xl bg-[#F1F4F8] text-[#0891B2] font-bold text-lg flex items-center justify-center mb-6">
                02
              </div>
              <h3 className="text-xl font-bold text-[#171C26] mb-3">
                Configure and validate
              </h3>
              <p className="text-sm text-[#647084] leading-relaxed">
                Supply your migration SQL DDL and define application query contracts. Contracts replay active production queries to ensure upcoming schema changes won&apos;t break them.
              </p>
            </div>
            <div className="mt-6 pt-4 border-t border-[#E5E9F0] text-xs font-medium text-[#929BA9]">
              Replays OLD_APP & NEW_APP queries in read-only mode
            </div>
          </div>

          {/* Card 03 */}
          <div className="card-elevated p-8 rounded-xl flex flex-col justify-between">
            <div>
              <div className="w-12 h-12 rounded-xl bg-[#F1F4F8] text-[#159B67] font-bold text-lg flex items-center justify-center mb-6">
                03
              </div>
              <h3 className="text-xl font-bold text-[#171C26] mb-3">
                Review audit evidence
              </h3>
              <p className="text-sm text-[#647084] leading-relaxed">
                Inspect side-by-side metrics, detailed structural schema diffs, table row deltas, and invariant violations. Export deterministic Markdown or JSON evidence packages for code reviews.
              </p>
            </div>
            <div className="mt-6 pt-4 border-t border-[#E5E9F0] text-xs font-medium text-[#929BA9]">
              Downloadable PR-ready reports with exact verdicts
            </div>
          </div>
        </div>
      </section>

      {/* Safety Principles Section */}
      <section id="safety" className="py-16 bg-[#FFFFFF] border-y border-[#E5E9F0]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="max-w-3xl mb-12">
            <h2 className="text-xs font-bold uppercase tracking-wider text-[#2563EB] mb-2">
              Security Architecture
            </h2>
            <p className="text-3xl font-extrabold text-[#171C26] tracking-tight">
              SchemaGuard&apos;s real security principles
            </p>
            <p className="mt-3 text-base text-[#647084]">
              Built from first principles to guarantee your live data remains completely untouched.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            <div className="p-6 rounded-xl bg-[#F7F8FA] border border-[#E5E9F0]">
              <div className="w-8 h-8 rounded-lg bg-[#2563EB]/10 text-[#2563EB] flex items-center justify-center mb-4">
                <Lock className="w-4 h-4 stroke-[2.2]" />
              </div>
              <h3 className="text-base font-bold text-[#171C26] mb-2">
                Read-Only Source Access
              </h3>
              <p className="text-xs text-[#647084] leading-relaxed">
                Source database files are opened strictly using SQLite URI parameter <code className="text-[#2563EB]">mode=ro</code>. The OS and SQLite engine forbid any write mutations.
              </p>
            </div>

            <div className="p-6 rounded-xl bg-[#F7F8FA] border border-[#E5E9F0]">
              <div className="w-8 h-8 rounded-lg bg-[#0891B2]/10 text-[#0891B2] flex items-center justify-center mb-4">
                <Layers className="w-4 h-4 stroke-[2.2]" />
              </div>
              <h3 className="text-base font-bold text-[#171C26] mb-2">
                Isolated Sandbox Copies
              </h3>
              <p className="text-xs text-[#647084] leading-relaxed">
                Every rehearsal creates a unique, disposable directory and uses SQLite&apos;s native backup API (<code className="text-[#0891B2]">sqlite3.backup</code>) to clone data safely.
              </p>
            </div>

            <div className="p-6 rounded-xl bg-[#F7F8FA] border border-[#E5E9F0]">
              <div className="w-8 h-8 rounded-lg bg-[#159B67]/10 text-[#159B67] flex items-center justify-center mb-4">
                <Shield className="w-4 h-4 stroke-[2.2]" />
              </div>
              <h3 className="text-base font-bold text-[#171C26] mb-2">
                Security Authorizer Boundary
              </h3>
              <p className="text-xs text-[#647084] leading-relaxed">
                SQLite&apos;s low-level <code className="text-[#159B67]">set_authorizer</code> callback denies dangerous operations including ATTACH, DETACH, writable_schema, and extension loading.
              </p>
            </div>

            <div className="p-6 rounded-xl bg-[#F7F8FA] border border-[#E5E9F0]">
              <div className="w-8 h-8 rounded-lg bg-[#2563EB]/10 text-[#2563EB] flex items-center justify-center mb-4">
                <Activity className="w-4 h-4 stroke-[2.2]" />
              </div>
              <h3 className="text-base font-bold text-[#171C26] mb-2">
                Application Contract Replay
              </h3>
              <p className="text-xs text-[#647084] leading-relaxed">
                Validates that critical queries (e.g. user authentication, order lookup) still execute cleanly after table modifications or dropped columns.
              </p>
            </div>

            <div className="p-6 rounded-xl bg-[#F7F8FA] border border-[#E5E9F0]">
              <div className="w-8 h-8 rounded-lg bg-[#D99A22]/10 text-[#D99A22] flex items-center justify-center mb-4">
                <CheckCircle2 className="w-4 h-4 stroke-[2.2]" />
              </div>
              <h3 className="text-base font-bold text-[#171C26] mb-2">
                Business Invariant Validation
              </h3>
              <p className="text-xs text-[#647084] leading-relaxed">
                Evaluates business domain rules (e.g. no negative totals, no orphaned orders). Invariants strictly require 0 violating rows to pass.
              </p>
            </div>

            <div className="p-6 rounded-xl bg-[#F7F8FA] border border-[#E5E9F0]">
              <div className="w-8 h-8 rounded-lg bg-[#DC4B4B]/10 text-[#DC4B4B] flex items-center justify-center mb-4">
                <AlertTriangle className="w-4 h-4 stroke-[2.2]" />
              </div>
              <h3 className="text-base font-bold text-[#171C26] mb-2">
                Honest Severity Labeling
              </h3>
              <p className="text-xs text-[#647084] leading-relaxed">
                We never make false claims of &quot;guaranteed safe&quot;. When all checks pass cleanly, the engine labels the report accurately: <strong>&quot;No configured checks failed&quot;</strong>.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Demo Scenarios Section */}
      <section className="py-16 md:py-24 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex flex-col md:flex-row md:items-end justify-between mb-12">
          <div>
            <h2 className="text-xs font-bold uppercase tracking-wider text-[#2563EB] mb-2">
              Instant Exploration
            </h2>
            <p className="text-3xl font-extrabold text-[#171C26] tracking-tight">
              Curated rehearsal scenarios
            </p>
            <p className="mt-2 text-sm text-[#647084]">
              Launch 1-click test scenarios pre-populated with synthetic eCommerce data.
            </p>
          </div>
          <Link
            href="/rehearsal"
            className="mt-4 md:mt-0 inline-flex items-center gap-1.5 text-sm font-semibold text-[#2563EB] hover:text-[#1D4ED8]"
          >
            <span>Open Rehearsal Studio</span>
            <ArrowRight className="w-4 h-4" />
          </Link>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Scenario 1: Safe Add Column */}
          <div className="card-elevated p-6 rounded-xl flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-4">
                <span className="text-xs font-bold uppercase tracking-wider text-[#159B67] bg-[#159B67]/10 border border-[#159B67]/20 px-2.5 py-0.5 rounded-md">
                  Passing Baseline
                </span>
                <span className="text-xs font-mono text-[#929BA9]">01_safe</span>
              </div>
              <h3 className="text-lg font-bold text-[#171C26] mb-2">
                Safe Column Addition
              </h3>
              <p className="text-xs text-[#647084] leading-relaxed mb-4">
                Appends <code className="text-[#2563EB]">phone TEXT</code> to <code className="text-[#2563EB]">users</code>. Both existing production contracts and upcoming contracts pass cleanly.
              </p>
              <div className="text-xs font-mono text-[#647084] bg-[#F1F4F8] p-3 rounded-lg border border-[#E5E9F0]">
                ALTER TABLE users ADD COLUMN phone TEXT;
              </div>
            </div>
            <div className="mt-6 pt-4 border-t border-[#E5E9F0]">
              <button
                onClick={() => handleLaunchScenario("safe")}
                className="w-full inline-flex items-center justify-center gap-2 px-4 py-2.5 text-xs font-bold text-white bg-[#2563EB] hover:bg-[#1D4ED8] rounded-lg transition-colors cursor-pointer"
              >
                <Play className="w-3.5 h-3.5 fill-current" />
                <span>Load Safe Scenario</span>
              </button>
            </div>
          </div>

          {/* Scenario 2: Breaking Query Contract */}
          <div className="card-elevated p-6 rounded-xl flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-4">
                <span className="text-xs font-bold uppercase tracking-wider text-[#DC4B4B] bg-[#DC4B4B]/10 border border-[#DC4B4B]/20 px-2.5 py-0.5 rounded-md">
                  Critical Break
                </span>
                <span className="text-xs font-mono text-[#929BA9]">02_break</span>
              </div>
              <h3 className="text-lg font-bold text-[#171C26] mb-2">
                Breaking Query Contract
              </h3>
              <p className="text-xs text-[#647084] leading-relaxed mb-4">
                Drops <code className="text-[#DC4B4B]">email</code> from <code className="text-[#2563EB]">users</code>. Triggers an immediate CRITICAL failure on the existing production application contract.
              </p>
              <div className="text-xs font-mono text-[#647084] bg-[#F1F4F8] p-3 rounded-lg border border-[#E5E9F0]">
                ALTER TABLE users DROP COLUMN email;
              </div>
            </div>
            <div className="mt-6 pt-4 border-t border-[#E5E9F0]">
              <button
                onClick={() => handleLaunchScenario("break_contract")}
                className="w-full inline-flex items-center justify-center gap-2 px-4 py-2.5 text-xs font-bold text-[#DC4B4B] bg-[#DC4B4B]/10 hover:bg-[#DC4B4B]/15 border border-[#DC4B4B]/25 rounded-lg transition-colors cursor-pointer"
              >
                <Play className="w-3.5 h-3.5 fill-current" />
                <span>Load Breaking Scenario</span>
              </button>
            </div>
          </div>

          {/* Scenario 3: Destructive Table Drop */}
          <div className="card-elevated p-6 rounded-xl flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-4">
                <span className="text-xs font-bold uppercase tracking-wider text-[#D99A22] bg-[#D99A22]/10 border border-[#D99A22]/20 px-2.5 py-0.5 rounded-md">
                  High Risk
                </span>
                <span className="text-xs font-mono text-[#929BA9]">03_drop</span>
              </div>
              <h3 className="text-lg font-bold text-[#171C26] mb-2">
                Destructive Table Drop
              </h3>
              <p className="text-xs text-[#647084] leading-relaxed mb-4">
                Executes <code className="text-[#D99A22]">DROP TABLE order_items</code>. Triggers AST static warnings, data profiling row drop flags, and structural removal alerts.
              </p>
              <div className="text-xs font-mono text-[#647084] bg-[#F1F4F8] p-3 rounded-lg border border-[#E5E9F0]">
                DROP TABLE order_items;
              </div>
            </div>
            <div className="mt-6 pt-4 border-t border-[#E5E9F0]">
              <button
                onClick={() => handleLaunchScenario("drop_table")}
                className="w-full inline-flex items-center justify-center gap-2 px-4 py-2.5 text-xs font-bold text-[#D99A22] bg-[#D99A22]/10 hover:bg-[#D99A22]/15 border border-[#D99A22]/25 rounded-lg transition-colors cursor-pointer"
              >
                <Play className="w-3.5 h-3.5 fill-current" />
                <span>Load Drop Table Scenario</span>
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* Final Callout Banner */}
      <section className="pb-20 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="glass-panel p-8 md:p-12 rounded-2xl flex flex-col md:flex-row items-center justify-between gap-8 border border-[#E5E9F0]">
          <div>
            <h3 className="text-2xl font-bold text-[#171C26] mb-2">
              Ready to verify your SQLite migration?
            </h3>
            <p className="text-sm text-[#647084] max-w-xl">
              Launch a rehearsal in under two seconds. Zero production risk, zero external dependencies, 100% deterministic evidence.
            </p>
          </div>
          <Link
            href="/rehearsal"
            className="inline-flex items-center gap-2 px-6 py-3.5 text-sm font-semibold text-white bg-[#2563EB] hover:bg-[#1D4ED8] rounded-xl shadow-md hover:shadow-lg transition-all"
          >
            <span>Configure Rehearsal</span>
            <ArrowRight className="w-4 h-4 stroke-[2.2]" />
          </Link>
        </div>
      </section>
    </div>
  );
}
