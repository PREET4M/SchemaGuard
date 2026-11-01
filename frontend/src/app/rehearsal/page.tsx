"use client";

import { useEffect, useState, useTransition, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  Database,
  Upload,
  Code2,
  Copy,
  Check,
  Play,
  Layers,
  Shield,
  Clock,
  AlertCircle,
  FileCode,
  FileCheck,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { DemoMetadata, RehearsalReport } from "@/types/schemaguard";

function RehearsalForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const scenarioParam = searchParams.get("scenario");

  const [metadata, setMetadata] = useState<DemoMetadata | null>(null);
  const [loadingMeta, setLoadingMeta] = useState(true);

  // Form states
  const [dbSourceType, setDbSourceType] = useState<"demo" | "upload">("demo");
  const [uploadedFileId, setUploadedFileId] = useState<string | null>(null);
  const [uploadedFileName, setUploadedFileName] = useState<string | null>(null);
  const [uploadedTables, setUploadedTables] = useState<Array<{ name: string; row_count: number }>>([]);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);

  const [presetChoice, setPresetChoice] = useState<string>("custom");
  const [migrationSql, setMigrationSql] = useState<string>("");
  const [oldContractsSql, setOldContractsSql] = useState<string>("");
  const [newContractsSql, setNewContractsSql] = useState<string>("");
  const [invariantsSql, setInvariantsSql] = useState<string>("");

  const [showContracts, setShowContracts] = useState<boolean>(true);
  const [showInvariants, setShowInvariants] = useState<boolean>(true);
  const [copied, setCopied] = useState<boolean>(false);

  // Execution states
  const [isExecuting, setIsExecuting] = useState<boolean>(false);
  const [executionError, setExecutionError] = useState<string | null>(null);

  // Load demo metadata on mount
  useEffect(() => {
    async function fetchMetadata() {
      try {
        setLoadingMeta(true);
        const res = await fetch("/api/demo/metadata");
        if (res.ok) {
          const data: DemoMetadata = await res.json();
          setMetadata(data);

          // Populate defaults
          setOldContractsSql(data.default_contracts.old_app_sql);
          setNewContractsSql(data.default_contracts.new_app_sql);
          setInvariantsSql(data.default_invariants_sql);

          if (scenarioParam && data.scenarios[scenarioParam as keyof typeof data.scenarios]) {
            const sc = data.scenarios[scenarioParam as keyof typeof data.scenarios];
            setPresetChoice(scenarioParam);
            setMigrationSql(sc.migration_sql);
          } else {
            setPresetChoice("safe");
            setMigrationSql(data.scenarios.safe.migration_sql);
          }
        }
      } catch (err) {
        console.error("Failed to load demo metadata:", err);
      } finally {
        setLoadingMeta(false);
      }
    }
    fetchMetadata();
  }, [scenarioParam]);

  // Handle Preset Change
  const handlePresetSelect = (key: string) => {
    setPresetChoice(key);
    if (!metadata) return;

    if (key === "safe") {
      setMigrationSql(metadata.scenarios.safe.migration_sql);
    } else if (key === "break_contract") {
      setMigrationSql(metadata.scenarios.break_contract.migration_sql);
    } else if (key === "drop_table") {
      setMigrationSql(metadata.scenarios.drop_table.migration_sql);
    }
  };

  // Handle Custom DB Upload
  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (file.size > 25 * 1024 * 1024) {
      setUploadError("File exceeds maximum permitted limit of 25 MB.");
      return;
    }

    setUploadError(null);
    setIsUploading(true);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch("/api/upload-database", {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || "Upload validation failed.");
      }

      const data = await res.json();
      setUploadedFileId(data.upload_id);
      setUploadedFileName(data.filename);
      setUploadedTables(data.tables || []);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Upload error";
      setUploadError(message);
    } finally {
      setIsUploading(false);
    }
  };

  // Helper to split SQL queries
  const splitQueries = (text: string): string[] => {
    const statements: string[] = [];
    let current: string[] = [];

    for (const line of text.split("\n")) {
      const trimmed = line.trim();
      if (!trimmed || trimmed.startsWith("--")) continue;
      current.push(line);
      if (line.includes(";")) {
        const stmt = current.join("\n").trim();
        if (stmt) statements.push(stmt);
        current = [];
      }
    }
    if (current.length > 0) {
      const trailing = current.join("\n").trim();
      if (trailing) statements.push(trailing);
    }
    return statements;
  };

  // Copy SQL snippet
  const handleCopySql = () => {
    navigator.clipboard.writeText(migrationSql);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // Execute Rehearsal
  const handleExecute = async () => {
    if (!migrationSql.trim()) {
      setExecutionError("Migration SQL cannot be empty. Please enter or select SQL statements.");
      return;
    }

    if (dbSourceType === "upload" && !uploadedFileId) {
      setExecutionError("Please upload a valid SQLite database file before executing.");
      return;
    }

    setExecutionError(null);
    setIsExecuting(true);

    const oldQueries = oldContractsSql.trim() ? splitQueries(oldContractsSql) : [];
    const newQueries = newContractsSql.trim() ? splitQueries(newContractsSql) : [];
    const invariantList = invariantsSql.trim() ? [invariantsSql.trim()] : [];

    const payload = {
      source_type: dbSourceType,
      upload_id: dbSourceType === "upload" ? uploadedFileId : null,
      migration_sql: migrationSql,
      old_app_contracts: oldQueries,
      new_app_contracts: newQueries,
      invariants: invariantList,
    };

    try {
      const res = await fetch("/api/rehearse", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const errJson = await res.json();
        throw new Error(errJson.detail || "Rehearsal execution failed.");
      }

      const report: RehearsalReport = await res.json();
      // Store report in sessionStorage for resilient fallback
      sessionStorage.setItem("latest_rehearsal_report", JSON.stringify(report));
      // Navigate to Results page with report ID
      router.push(`/results?id=${report.rehearsal_id}`);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Unknown rehearsal error";
      setExecutionError(msg);
      setIsExecuting(false);
    }
  };

  const oldContractCount = splitQueries(oldContractsSql).length;
  const newContractCount = splitQueries(newContractsSql).length;
  const invariantCount = invariantsSql.trim() ? 1 : 0;

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      {/* Workflow Progress Breadcrumb */}
      <div className="flex items-center gap-2 text-xs font-semibold text-[#929BA9] mb-4">
        <span className="text-[#2563EB]">01. Source & Migration</span>
        <span>→</span>
        <span className="text-[#2563EB]">02. Verification Rules</span>
        <span>→</span>
        <span>03. Isolated Execution</span>
      </div>

      {/* Page Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-extrabold text-[#171C26] tracking-tight">
          Configure your rehearsal
        </h1>
        <p className="mt-2 text-sm text-[#647084]">
          Select a database, prepare your migration, and configure validation checks. All operations run exclusively inside isolated temporary SQLite clones.
        </p>
      </div>

      <div className="space-y-8">
        {/* SECTION 01: SOURCE DATABASE */}
        <section className="bg-[#FFFFFF] border border-[#E5E9F0] rounded-xl p-6 shadow-sm">
          <div className="flex items-center gap-2.5 mb-4 pb-3 border-b border-[#E5E9F0]">
            <div className="w-8 h-8 rounded-lg bg-[#2563EB]/10 text-[#2563EB] flex items-center justify-center">
              <Database className="w-4 h-4 stroke-[2.2]" />
            </div>
            <div>
              <h2 className="text-base font-bold text-[#171C26]">
                Section 01: Source Database
              </h2>
              <p className="text-xs text-[#647084]">
                Source is opened strictly in read-only mode (<code className="text-[#2563EB]">mode=ro</code>) and cloned into a disposable sandbox.
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-4">
            <button
              type="button"
              onClick={() => setDbSourceType("demo")}
              className={`p-4 rounded-xl border text-left transition-all cursor-pointer ${
                dbSourceType === "demo"
                  ? "border-[#2563EB] bg-[#2563EB]/5 ring-1 ring-[#2563EB]"
                  : "border-[#E5E9F0] hover:bg-[#F7F8FA]"
              }`}
            >
              <div className="flex items-center justify-between mb-1">
                <span className="text-sm font-bold text-[#171C26]">Synthetic Demo DB</span>
                <span className="text-[11px] font-semibold text-[#159B67] bg-[#159B67]/10 px-2 py-0.5 rounded">Ready</span>
              </div>
              <p className="text-xs text-[#647084]">
                ecommerce.db with 10 synthetic users, 5 products, and 12 orders.
              </p>
            </button>

            <button
              type="button"
              onClick={() => setDbSourceType("upload")}
              className={`p-4 rounded-xl border text-left transition-all cursor-pointer ${
                dbSourceType === "upload"
                  ? "border-[#2563EB] bg-[#2563EB]/5 ring-1 ring-[#2563EB]"
                  : "border-[#E5E9F0] hover:bg-[#F7F8FA]"
              }`}
            >
              <div className="flex items-center justify-between mb-1">
                <span className="text-sm font-bold text-[#171C26]">Upload Custom SQLite DB</span>
                <span className="text-[11px] font-semibold text-[#647084] bg-[#F1F4F8] px-2 py-0.5 rounded">Custom</span>
              </div>
              <p className="text-xs text-[#647084]">
                Upload your own .db, .sqlite, or .sqlite3 file (up to 25 MB).
              </p>
            </button>
          </div>

          {/* Source Details */}
          {dbSourceType === "demo" ? (
            <div className="bg-[#F7F8FA] p-4 rounded-lg border border-[#E5E9F0]">
              <div className="text-xs font-bold uppercase tracking-wider text-[#929BA9] mb-2">
                Available Tables & Baseline Row Counts
              </div>
              {loadingMeta ? (
                <div className="text-xs text-[#647084]">Loading database schema...</div>
              ) : (
                <div className="flex flex-wrap gap-2">
                  {metadata?.tables.map((tbl) => (
                    <span
                      key={tbl.name}
                      className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-[#FFFFFF] border border-[#E5E9F0] text-xs font-mono text-[#171C26]"
                    >
                      <span className="font-semibold">{tbl.name}</span>
                      <span className="text-[#2563EB] font-bold">({tbl.row_count})</span>
                    </span>
                  ))}
                </div>
              )}
            </div>
          ) : (
            <div className="space-y-3">
              <div className="border-2 border-dashed border-[#E5E9F0] hover:border-[#2563EB]/50 rounded-xl p-6 text-center bg-[#F7F8FA] transition-colors">
                <Upload className="w-8 h-8 text-[#929BA9] mx-auto mb-2" />
                <label className="cursor-pointer">
                  <span className="text-sm font-semibold text-[#2563EB] hover:text-[#1D4ED8]">
                    Click to upload database file
                  </span>
                  <input
                    type="file"
                    accept=".db,.sqlite,.sqlite3"
                    className="hidden"
                    onChange={handleFileUpload}
                  />
                </label>
                <p className="text-xs text-[#929BA9] mt-1">
                  SQLite 3 format only • Max 25 MB
                </p>
              </div>

              {isUploading && (
                <div className="text-xs text-[#2563EB] font-medium flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full border-2 border-[#2563EB] border-t-transparent animate-spin" />
                  <span>Validating SQLite header and copying to sandbox...</span>
                </div>
              )}

              {uploadedFileName && (
                <div className="p-3 bg-[#159B67]/10 border border-[#159B67]/25 rounded-lg text-xs text-[#159B67] flex items-center justify-between">
                  <span>Uploaded: <strong>{uploadedFileName}</strong></span>
                  <span>{uploadedTables.length} table(s) found</span>
                </div>
              )}

              {uploadError && (
                <div className="p-3 bg-[#DC4B4B]/10 border border-[#DC4B4B]/25 rounded-lg text-xs text-[#DC4B4B]">
                  {uploadError}
                </div>
              )}
            </div>
          )}
        </section>

        {/* SECTION 02: MIGRATION SQL */}
        <section className="bg-[#FFFFFF] border border-[#E5E9F0] rounded-xl p-6 shadow-sm">
          <div className="flex items-center justify-between mb-4 pb-3 border-b border-[#E5E9F0]">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-lg bg-[#0891B2]/10 text-[#0891B2] flex items-center justify-center">
                <Code2 className="w-4 h-4 stroke-[2.2]" />
              </div>
              <div>
                <h2 className="text-base font-bold text-[#171C26]">
                  Section 02: Migration SQL DDL
                </h2>
                <p className="text-xs text-[#647084]">
                  Statements to apply exclusively against the isolated sandbox copy.
                </p>
              </div>
            </div>

            {/* Copy button */}
            <button
              type="button"
              onClick={handleCopySql}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-[#647084] hover:text-[#171C26] bg-[#F1F4F8] hover:bg-[#E5E9F0] rounded-lg transition-colors cursor-pointer"
            >
              {copied ? (
                <>
                  <Check className="w-3.5 h-3.5 text-[#159B67]" />
                  <span>Copied</span>
                </>
              ) : (
                <>
                  <Copy className="w-3.5 h-3.5" />
                  <span>Copy SQL</span>
                </>
              )}
            </button>
          </div>

          {/* Preset Selector */}
          <div className="mb-4">
            <label className="block text-xs font-bold uppercase tracking-wider text-[#929BA9] mb-1.5">
              Select Preset or Custom
            </label>
            <select
              value={presetChoice}
              onChange={(e) => handlePresetSelect(e.target.value)}
              className="w-full sm:w-auto px-3.5 py-2 text-sm bg-[#FFFFFF] border border-[#E5E9F0] rounded-lg text-[#171C26] focus:outline-none focus:border-[#2563EB] focus:ring-2 focus:ring-[#2563EB]/15"
            >
              <option value="custom">Custom SQL</option>
              <option value="safe">01_safe_add_column.sql (Safe: Add phone)</option>
              <option value="break_contract">02_break_old_query.sql (Breaking: Drop email)</option>
              <option value="drop_table">03_drop_table.sql (Destructive: Drop order_items)</option>
            </select>
          </div>

          {/* SQL Editor */}
          <div>
            <textarea
              rows={6}
              value={migrationSql}
              onChange={(e) => {
                setMigrationSql(e.target.value);
                setPresetChoice("custom");
              }}
              placeholder="-- Enter your migration DDL statements here&#10;ALTER TABLE users ADD COLUMN phone TEXT;"
              className="w-full p-4 light-code-editor text-xs sm:text-sm font-mono border rounded-lg focus:outline-none"
            />
            <p className="mt-1.5 text-xs text-[#929BA9]">
              Supports multiple statements separated by semicolons. Transactional rollback occurs automatically on syntax error.
            </p>
          </div>
        </section>

        {/* SECTION 03: APPLICATION CONTRACTS */}
        <section className="bg-[#FFFFFF] border border-[#E5E9F0] rounded-xl p-6 shadow-sm">
          <div className="flex items-center justify-between mb-4 pb-3 border-b border-[#E5E9F0]">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-lg bg-[#2563EB]/10 text-[#2563EB] flex items-center justify-center">
                <FileCode className="w-4 h-4 stroke-[2.2]" />
              </div>
              <div>
                <h2 className="text-base font-bold text-[#171C26]">
                  Section 03: Application Query Contracts
                </h2>
                <p className="text-xs text-[#647084]">
                  Queries replayed against the post-migration sandbox to verify application compatibility.
                </p>
              </div>
            </div>

            <button
              type="button"
              onClick={() => setShowContracts(!showContracts)}
              className="p-1.5 text-[#647084] hover:text-[#171C26] rounded-lg hover:bg-[#F1F4F8]"
            >
              {showContracts ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
            </button>
          </div>

          {showContracts && (
            <div className="space-y-4">
              {/* OLD_APP Contracts */}
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label className="text-xs font-bold uppercase tracking-wider text-[#171C26]">
                    Production Contracts (OLD_APP)
                  </label>
                  <span className="text-[11px] font-semibold text-[#DC4B4B] bg-[#DC4B4B]/10 px-2 py-0.5 rounded">
                    Failure triggers CRITICAL risk
                  </span>
                </div>
                <textarea
                  rows={4}
                  value={oldContractsSql}
                  onChange={(e) => setOldContractsSql(e.target.value)}
                  placeholder="-- Production query contract&#10;SELECT id, name, email FROM users WHERE id = 1;"
                  className="w-full p-3 light-code-editor text-xs font-mono border rounded-lg focus:outline-none"
                />
                <p className="text-[11px] text-[#647084] mt-1">
                  Queries actively running in production services. If any fail post-migration, SchemaGuard flags an immediate CRITICAL failure.
                </p>
              </div>

              {/* NEW_APP Contracts */}
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label className="text-xs font-bold uppercase tracking-wider text-[#171C26]">
                    Upcoming Contracts (NEW_APP)
                  </label>
                  <span className="text-[11px] font-semibold text-[#D99A22] bg-[#D99A22]/10 px-2 py-0.5 rounded">
                    Failure triggers MODERATE risk
                  </span>
                </div>
                <textarea
                  rows={4}
                  value={newContractsSql}
                  onChange={(e) => setNewContractsSql(e.target.value)}
                  placeholder="-- Upcoming query contract&#10;SELECT id, name, phone FROM users WHERE id = 1;"
                  className="w-full p-3 light-code-editor text-xs font-mono border rounded-lg focus:outline-none"
                />
                <p className="text-[11px] text-[#647084] mt-1">
                  Queries expected by the upcoming software release.
                </p>
              </div>
            </div>
          )}
        </section>

        {/* SECTION 04: BUSINESS INVARIANTS */}
        <section className="bg-[#FFFFFF] border border-[#E5E9F0] rounded-xl p-6 shadow-sm">
          <div className="flex items-center justify-between mb-4 pb-3 border-b border-[#E5E9F0]">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-lg bg-[#D99A22]/10 text-[#D99A22] flex items-center justify-center">
                <FileCheck className="w-4 h-4 stroke-[2.2]" />
              </div>
              <div>
                <h2 className="text-base font-bold text-[#171C26]">
                  Section 04: Business Invariants (Assertions)
                </h2>
                <p className="text-xs text-[#647084]">
                  Queries that search for corrupted or orphaned data. <strong>Must return 0 rows to pass.</strong>
                </p>
              </div>
            </div>

            <button
              type="button"
              onClick={() => setShowInvariants(!showInvariants)}
              className="p-1.5 text-[#647084] hover:text-[#171C26] rounded-lg hover:bg-[#F1F4F8]"
            >
              {showInvariants ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
            </button>
          </div>

          {showInvariants && (
            <div>
              <textarea
                rows={5}
                value={invariantsSql}
                onChange={(e) => setInvariantsSql(e.target.value)}
                placeholder="-- Invariant: No negative order totals&#10;SELECT id, total FROM orders WHERE total < 0;&#10;&#10;-- Invariant: No orphaned order items&#10;SELECT oi.id FROM order_items oi LEFT JOIN orders o ON oi.order_id = o.id WHERE o.id IS NULL;"
                className="w-full p-3 light-code-editor text-xs font-mono border rounded-lg focus:outline-none"
              />
              <p className="text-[11px] text-[#647084] mt-1">
                Rule: If any rows are returned, the invariant fails. Failure triggers HIGH risk.
              </p>
            </div>
          )}
        </section>

        {/* SECTION 05: EXECUTION CONSTRAINTS & BOUNDARY */}
        <section className="bg-[#F7F8FA] border border-[#E5E9F0] rounded-xl p-5">
          <div className="text-xs font-bold uppercase tracking-wider text-[#929BA9] mb-3 flex items-center gap-1.5">
            <Shield className="w-3.5 h-3.5 text-[#2563EB]" />
            <span>Execution Sandbox & Safety Guarantees</span>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs">
            <div>
              <span className="text-[#647084] block">Source Isolation:</span>
              <strong className="text-[#171C26]">Read-Only (mode=ro)</strong>
            </div>
            <div>
              <span className="text-[#647084] block">Execution Copy:</span>
              <strong className="text-[#171C26]">SQLite Backup API Clone</strong>
            </div>
            <div>
              <span className="text-[#647084] block">Timeout Limit:</span>
              <strong className="text-[#171C26]">5.0 seconds</strong>
            </div>
            <div>
              <span className="text-[#647084] block">Max DB Size:</span>
              <strong className="text-[#171C26]">25 MB</strong>
            </div>
          </div>
        </section>

        {/* FINAL EXECUTION SECTION */}
        <section className="bg-[#FFFFFF] border-2 border-[#2563EB]/30 rounded-xl p-6 shadow-md">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6 pb-4 border-b border-[#E5E9F0]">
            <div>
              <h3 className="text-lg font-bold text-[#171C26]">
                Ready for Isolated Rehearsal
              </h3>
              <p className="text-xs text-[#647084]">
                Confirm your configuration summary before executing in the temporary sandbox.
              </p>
            </div>

            {/* Quick Summary Chips */}
            <div className="flex flex-wrap items-center gap-2 text-xs">
              <span className="px-2.5 py-1 rounded bg-[#F1F4F8] border border-[#E5E9F0] font-medium text-[#171C26]">
                DB: {dbSourceType === "demo" ? "ecommerce.db" : uploadedFileName || "Custom"}
              </span>
              <span className="px-2.5 py-1 rounded bg-[#F1F4F8] border border-[#E5E9F0] font-medium text-[#171C26]">
                Contracts: {oldContractCount + newContractCount}
              </span>
              <span className="px-2.5 py-1 rounded bg-[#F1F4F8] border border-[#E5E9F0] font-medium text-[#171C26]">
                Invariants: {invariantCount}
              </span>
            </div>
          </div>

          {executionError && (
            <div className="mb-4 p-4 bg-[#DC4B4B]/10 border border-[#DC4B4B]/30 rounded-lg text-xs text-[#DC4B4B] flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{executionError}</span>
            </div>
          )}

          <button
            type="button"
            disabled={isExecuting}
            onClick={handleExecute}
            className={`w-full py-4 px-6 rounded-xl font-bold text-sm tracking-wide text-white transition-all duration-150 flex items-center justify-center gap-2 cursor-pointer ${
              isExecuting
                ? "bg-[#2563EB]/70 cursor-not-allowed"
                : "bg-[#2563EB] hover:bg-[#1D4ED8] active:bg-[#1E40AF] shadow-md hover:shadow-lg"
            }`}
          >
            {isExecuting ? (
              <>
                <div className="w-4 h-4 rounded-full border-2 border-white border-t-transparent animate-spin" />
                <span>Executing Rehearsal in Isolated Sandbox Copy...</span>
              </>
            ) : (
              <>
                <Play className="w-4 h-4 fill-current" />
                <span>Execute Isolated Rehearsal</span>
              </>
            )}
          </button>
        </section>
      </div>
    </div>
  );
}

export default function RehearsalPage() {
  return (
    <Suspense fallback={<div className="max-w-5xl mx-auto p-12 text-center text-sm text-[#647084]">Loading rehearsal studio...</div>}>
      <RehearsalForm />
    </Suspense>
  );
}
