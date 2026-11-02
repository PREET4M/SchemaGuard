"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import {
  ArrowRight, Database, Shield, Lock, CheckCircle2,
  FileCode2, Activity, Layers, Play, AlertTriangle, Zap,
} from "lucide-react";

const fade = (delay = 0) => ({
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.5, delay, ease: "easeOut" as const },
});

const PIPELINE = [
  { icon: Database,    label: "Source DB",       color: "#2563EB", desc: "Your real SQLite file"            },
  { icon: FileCode2,  label: "Migration SQL",    color: "#0891B2", desc: "ALTER, CREATE, DROP statements"   },
  { icon: Shield,     label: "Sandbox Clone",    color: "#159B67", desc: "Isolated copy via Backup API"     },
  { icon: CheckCircle2, label: "Verification",   color: "#D99A22", desc: "Contracts · Invariants · Diff"   },
  { icon: Activity,   label: "Risk Report",      color: "#DC4B4B", desc: "LOW → CRITICAL severity"         },
];

const SECURITY = [
  { icon: Lock,         title: "Zero Production Writes", desc: "SQLite Backup API clone. Your source file is never touched." },
  { icon: Shield,       title: "SQL Authorizer",         desc: "Set_authorizer blocks ATTACH, DROP, PRAGMA writes at kernel level." },
  { icon: Layers,       title: "Sandbox Isolation",      desc: "Unique temp directory per run. Destroyed after reporting." },
  { icon: FileCode2,    title: "Static Analysis",        desc: "SQLGlot AST parse detects DROP TABLE, column removals before execution." },
  { icon: CheckCircle2, title: "Contract Replay",        desc: "OLD_APP and NEW_APP SQL queries verified against post-migration schema." },
  { icon: Activity,     title: "Row Invariants",         desc: "User-defined invariant queries must return zero rows to PASS." },
];

const SCENARIOS = [
  {
    key: "safe_migration",
    label: "LOW — Safe",
    labelColor: "#159B67",
    labelBg: "bg-[#159B67]/10",
    labelBorder: "border-[#159B67]/20",
    title: "Safe Schema Addition",
    desc: "Adds a nullable column. All existing app contracts continue to execute. No row data lost.",
    sql: "ALTER TABLE users ADD COLUMN avatar_url TEXT;",
    btnCls: "text-[#159B67] bg-[#159B67]/10 hover:bg-[#159B67]/15 border-[#159B67]/25",
    btnLabel: "Load Safe Scenario",
    id: "01_safe",
  },
  {
    key: "break_contract",
    label: "CRITICAL — Break",
    labelColor: "#DC4B4B",
    labelBg: "bg-[#DC4B4B]/10",
    labelBorder: "border-[#DC4B4B]/20",
    title: "Breaking Query Contract",
    desc: "Drops the email column from users. Immediately fails the production application query contract.",
    sql: "ALTER TABLE users DROP COLUMN email;",
    btnCls: "text-[#DC4B4B] bg-[#DC4B4B]/10 hover:bg-[#DC4B4B]/15 border-[#DC4B4B]/25",
    btnLabel: "Load Breaking Scenario",
    id: "02_break",
  },
  {
    key: "drop_table",
    label: "HIGH — Destructive",
    labelColor: "#D99A22",
    labelBg: "bg-[#D99A22]/10",
    labelBorder: "border-[#D99A22]/20",
    title: "Destructive Table Drop",
    desc: "Executes DROP TABLE order_items. Triggers static warnings, row-count profiling, and structural alerts.",
    sql: "DROP TABLE order_items;",
    btnCls: "text-[#D99A22] bg-[#D99A22]/10 hover:bg-[#D99A22]/15 border-[#D99A22]/25",
    btnLabel: "Load Drop Scenario",
    id: "03_drop",
  },
];

export default function LandingPage() {
  const router = useRouter();

  return (
    <div className="relative overflow-hidden">
      {/* Ambient radial glow */}
      <div
        aria-hidden
        className="pointer-events-none absolute top-0 left-1/2 -translate-x-1/2 w-[900px] h-[500px] opacity-30"
        style={{ background: "radial-gradient(ellipse at 50% 0%, #2563EB33 0%, transparent 70%)" }}
      />

      {/* ── HERO ──────────────────────────────────────────── */}
      <section className="relative pt-20 pb-16 md:pt-28 md:pb-24 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
        <motion.div {...fade(0)} className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-lg bg-white border border-[#E5E9F0] text-xs font-semibold text-[#2563EB] shadow-sm mb-6">
          <span className="w-2 h-2 rounded-full bg-[#159B67] animate-pulse" />
          Local-First SQLite Migration Verification Engine
        </motion.div>

        <motion.h1 {...fade(0.1)} className="text-4xl sm:text-5xl md:text-[3.5rem] font-extrabold tracking-tight text-[#171C26] max-w-4xl mx-auto leading-[1.1]">
          Validate database migrations<br className="hidden sm:block" /> before they reach production.
        </motion.h1>

        <motion.p {...fade(0.2)} className="mt-6 text-lg text-[#647084] max-w-2xl mx-auto leading-relaxed">
          Rehearse schema changes against real application contracts in an isolated sandbox.
          Detect breaking changes — before deployment.
        </motion.p>

        <motion.div {...fade(0.3)} className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-3">
          <Link href="/rehearsal" className="btn-primary px-6 py-3 text-sm shadow-md hover:shadow-lg">
            Start Rehearsal <ArrowRight className="w-4 h-4" strokeWidth={2.2} />
          </Link>
          <a href="#how-it-works" className="btn-outline px-6 py-3 text-sm">
            How It Works
          </a>
        </motion.div>

        {/* Trust pills */}
        <motion.div {...fade(0.4)} className="mt-10 flex flex-wrap items-center justify-center gap-5 text-xs font-medium text-[#647084]">
          {[
            { icon: Lock,         txt: "Zero Production Writes"      },
            { icon: Shield,       txt: "SQLite Backup API Clones"    },
            { icon: CheckCircle2, txt: "Deterministic Evidence"      },
          ].map(({ icon: Icon, txt }) => (
            <div key={txt} className="flex items-center gap-1.5">
              <Icon className="w-3.5 h-3.5 text-[#2563EB]" />
              <span>{txt}</span>
            </div>
          ))}
        </motion.div>
      </section>

      {/* ── PIPELINE DIAGRAM ─────────────────────────────── */}
      <section id="how-it-works" className="py-14 md:py-20 bg-white border-y border-[#E5E9F0]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-12">
            <p className="text-xs font-bold uppercase tracking-widest text-[#2563EB] mb-2">Automated Rehearsal Pipeline</p>
            <h2 className="text-2xl md:text-3xl font-bold text-[#171C26] tracking-tight">
              How SchemaGuard proves migration safety
            </h2>
          </div>

          {/* Pipeline nodes */}
          <div className="flex flex-col md:flex-row items-center justify-center gap-0">
            {PIPELINE.map((node, i) => (
              <div key={node.label} className="flex flex-col md:flex-row items-center">
                <motion.div
                  initial={{ opacity: 0, scale: 0.9 }}
                  whileInView={{ opacity: 1, scale: 1 }}
                  viewport={{ once: true }}
                  transition={{ delay: i * 0.1, duration: 0.4 }}
                  className="flex flex-col items-center text-center w-40"
                >
                  <div
                    className="w-14 h-14 rounded-2xl flex items-center justify-center mb-3 shadow-sm border"
                    style={{ background: `${node.color}12`, borderColor: `${node.color}30` }}
                  >
                    <node.icon className="w-6 h-6" style={{ color: node.color }} strokeWidth={2} />
                  </div>
                  <p className="text-sm font-bold text-[#171C26] mb-1">{node.label}</p>
                  <p className="text-[11px] text-[#929BA9] leading-tight">{node.desc}</p>
                </motion.div>
                {i < PIPELINE.length - 1 && (
                  <div className="w-px h-6 md:h-px md:w-8 bg-[#E5E9F0] mx-2 flex-shrink-0" />
                )}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── SECURITY GRID ────────────────────────────────── */}
      <section className="py-16 md:py-24 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-12">
          <p className="text-xs font-bold uppercase tracking-widest text-[#2563EB] mb-2">Security Architecture</p>
          <h2 className="text-2xl md:text-3xl font-bold text-[#171C26] tracking-tight">
            Designed for production safety
          </h2>
          <p className="mt-3 text-sm text-[#647084] max-w-xl mx-auto">
            Every decision in SchemaGuard&apos;s design prioritizes one thing: your production database is never touched.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {SECURITY.map((s, i) => (
            <motion.div
              key={s.title}
              initial={{ opacity: 0, y: 12 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.07, duration: 0.4 }}
              className="card-elevated p-5 rounded-xl"
            >
              <div className="w-8 h-8 rounded-lg bg-[#2563EB]/10 flex items-center justify-center mb-3">
                <s.icon className="w-4 h-4 text-[#2563EB]" strokeWidth={2} />
              </div>
              <h3 className="text-sm font-bold text-[#171C26] mb-1">{s.title}</h3>
              <p className="text-xs text-[#647084] leading-relaxed">{s.desc}</p>
            </motion.div>
          ))}
        </div>
      </section>

      {/* ── DEMO SCENARIOS ────────────────────────────────── */}
      <section className="py-16 md:py-24 bg-[#F1F4F8] border-y border-[#E5E9F0]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-12">
            <p className="text-xs font-bold uppercase tracking-widest text-[#2563EB] mb-2">Demo Scenarios</p>
            <h2 className="text-2xl md:text-3xl font-bold text-[#171C26] tracking-tight">
              Instant scenario exploration
            </h2>
            <p className="mt-3 text-sm text-[#647084] max-w-xl mx-auto">
              Pre-configured migrations that showcase the full verification pipeline. Click any card to load it instantly.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            {SCENARIOS.map((s, i) => (
              <motion.div
                key={s.key}
                initial={{ opacity: 0, y: 14 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.1, duration: 0.4 }}
                className="card-elevated p-6 rounded-xl flex flex-col bg-white"
              >
                <div className="flex items-center justify-between mb-4">
                  <span className={`badge text-xs font-bold uppercase tracking-wide px-2.5 py-0.5 rounded-md border ${s.labelBg} ${s.labelBorder}`} style={{ color: s.labelColor }}>
                    {s.label}
                  </span>
                  <span className="text-[10px] font-mono text-[#929BA9]">{s.id}</span>
                </div>
                <h3 className="text-base font-bold text-[#171C26] mb-2">{s.title}</h3>
                <p className="text-xs text-[#647084] leading-relaxed mb-4 flex-1">{s.desc}</p>
                <div className="text-[11px] font-mono text-[#647084] bg-[#F7F8FA] p-3 rounded-lg border border-[#E5E9F0] mb-4">
                  {s.sql}
                </div>
                <button
                  onClick={() => router.push(`/rehearsal?scenario=${s.key}`)}
                  className={`w-full inline-flex items-center justify-center gap-2 px-4 py-2.5 text-xs font-bold border rounded-lg transition-colors ${s.btnCls}`}
                >
                  <Play className="w-3.5 h-3.5 fill-current" />
                  {s.btnLabel}
                </button>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ── CTA BANNER ────────────────────────────────────── */}
      <section className="py-16 md:py-24 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="glass-panel p-8 md:p-12 rounded-2xl flex flex-col md:flex-row items-center justify-between gap-8"
        >
          <div>
            <div className="flex items-center gap-2 mb-3">
              <Zap className="w-4 h-4 text-[#2563EB]" />
              <span className="text-xs font-bold uppercase tracking-widest text-[#2563EB]">Ready to start?</span>
            </div>
            <h3 className="text-2xl font-bold text-[#171C26] mb-2">
              Verify your SQLite migration now.
            </h3>
            <p className="text-sm text-[#647084] max-w-md">
              Launch a full rehearsal in under two seconds. Zero production risk, zero external dependencies, 100% deterministic evidence.
            </p>
          </div>
          <Link href="/rehearsal" className="btn-primary px-6 py-3.5 text-sm shadow-md whitespace-nowrap">
            Configure Rehearsal <ArrowRight className="w-4 h-4" strokeWidth={2.2} />
          </Link>
        </motion.div>
      </section>
    </div>
  );
}
