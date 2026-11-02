import Link from "next/link";
import { ArrowLeft, ShieldAlert, CheckCircle2 } from "lucide-react";

export default function TermsPage() {
  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <div className="mb-6">
        <Link
          href="/"
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-[#647084] hover:text-[#171C26] transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Back to Home</span>
        </Link>
      </div>

      <div className="mb-10 pb-6 border-b border-[#E5E9F0]">
        <h1 className="text-3xl font-extrabold text-[#171C26] tracking-tight">
          Terms & Rehearsal Scope
        </h1>
        <p className="mt-2 text-xs font-medium text-[#929BA9]">
          Last Updated: November 2026 • Local-First Architecture
        </p>
      </div>

      <div className="space-y-8 text-sm text-[#647084] leading-relaxed">
        {/* Core Disclaimer Callout */}
        <div className="p-5 bg-[#D99A22]/10 border border-[#D99A22]/25 rounded-xl text-xs text-[#171C26]">
          <div className="flex items-center gap-2 font-bold text-[#D99A22] mb-1.5">
            <ShieldAlert className="w-4 h-4" />
            <span>Essential Rehearsal Scope & Disclaimer</span>
          </div>
          SchemaGuard is a local database migration rehearsal and verification tool. It provides deterministic evidence regarding whether tested application contracts and data invariants held in an isolated sandbox clone. Passing rehearsal checks <strong>do not guarantee absolute safety</strong> or the complete absence of edge cases, race conditions, or performance anomalies in production environments.
        </div>

        {/* Section 1 */}
        <section>
          <h2 className="text-base font-bold text-[#171C26] mb-2">
            1. Sandbox Isolation & Zero Production Touch
          </h2>
          <p>
            SchemaGuard operates on a strict zero-production-write policy. All source databases are opened exclusively using SQLite URI parameters set to read-only (<code className="text-[#2563EB]">mode=ro</code>). All migration DDL and DML operations execute only against disposable temporary database copies created via the native SQLite Online Backup API.
          </p>
        </section>

        {/* Section 2 */}
        <section>
          <h2 className="text-base font-bold text-[#171C26] mb-2">
            2. Rehearsal Boundaries & Authorizer Restrictions
          </h2>
          <p>
            To prevent security escalations and database corruption, SchemaGuard enforces low-level SQLite authorizer rules. Commands attempting to attach external databases (<code className="text-[#2563EB]">ATTACH</code>/<code className="text-[#2563EB]">DETACH</code>), alter internal sqlite catalogs (<code className="text-[#2563EB]">PRAGMA writable_schema</code>), or load compiled extensions are blocked and rejected by design.
          </p>
        </section>

        {/* Section 3 */}
        <section>
          <h2 className="text-base font-bold text-[#171C26] mb-2">
            3. Verification Methodology & Contracts
          </h2>
          <p>
            Rehearsal outcomes reflect the validity of provided application query contracts and domain invariant assertions:
          </p>
          <ul className="list-disc pl-5 mt-2 space-y-1.5 text-xs">
            <li>
              <strong>Production Contracts (OLD_APP)</strong>: Queries that must remain compatible post-migration. Any failures trigger an immediate CRITICAL severity.
            </li>
            <li>
              <strong>Upcoming Contracts (NEW_APP)</strong>: Queries expected by the upcoming release. Failures trigger a MODERATE severity.
            </li>
            <li>
              <strong>Data Invariants</strong>: Assertions verifying data consistency. Invariants strictly require 0 returned rows to pass.
            </li>
          </ul>
        </section>

        {/* Section 4 */}
        <section>
          <h2 className="text-base font-bold text-[#171C26] mb-2">
            4. Local-First Operation & Telemetry
          </h2>
          <p>
            SchemaGuard executes entirely on your local infrastructure. No schema metadata, database contents, SQL statements, or query results are transmitted to external servers, cloud providers, or third-party artificial intelligence models.
          </p>
        </section>

        {/* Section 5 */}
        <section>
          <h2 className="text-base font-bold text-[#171C26] mb-2">
            5. Recommendations for Deployment
          </h2>
          <p>
            Always review the generated Markdown and JSON rehearsal audit reports, attach them to your pull request reviews, and run final end-to-end integration tests in a staging environment prior to production deployment.
          </p>
        </section>
      </div>
    </div>
  );
}

