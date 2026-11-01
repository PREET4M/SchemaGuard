import Link from "next/link";
import { ShieldCheck, Lock, ExternalLink } from "lucide-react";

export default function Footer() {
  return (
    <footer className="w-full bg-[#FFFFFF] border-t border-[#E5E9F0] mt-24">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8 mb-10">
          {/* Brand & Summary */}
          <div className="md:col-span-2 space-y-3">
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-lg bg-[#2563EB]/10 border border-[#2563EB]/25 flex items-center justify-center text-[#2563EB]">
                <ShieldCheck className="w-4 h-4 stroke-[2.2]" />
              </div>
              <span className="text-base font-bold text-[#171C26]">SchemaGuard</span>
            </div>
            <p className="text-sm text-[#647084] max-w-md leading-relaxed">
              Local-first SQLite database migration rehearsal and application compatibility verification. Rehearse schema alterations against real application queries in an isolated sandbox before deployment.
            </p>
            <div className="inline-flex items-center gap-1.5 text-xs font-semibold text-[#159B67] bg-[#159B67]/10 px-2.5 py-1 rounded-md border border-[#159B67]/20">
              <Lock className="w-3.5 h-3.5" />
              <span>Zero Production Writes • 100% Sandbox Isolation</span>
            </div>
          </div>

          {/* Product Links */}
          <div>
            <h4 className="text-xs font-bold uppercase tracking-wider text-[#929BA9] mb-3">
              Navigation
            </h4>
            <ul className="space-y-2 text-sm">
              <li>
                <Link href="/" className="text-[#647084] hover:text-[#171C26] transition-colors">
                  Product Overview
                </Link>
              </li>
              <li>
                <Link href="/rehearsal" className="text-[#647084] hover:text-[#171C26] transition-colors">
                  Rehearsal Workspace
                </Link>
              </li>
              <li>
                <Link href="/settings" className="text-[#647084] hover:text-[#171C26] transition-colors">
                  Settings & Limits
                </Link>
              </li>
            </ul>
          </div>

          {/* Legal / Policy */}
          <div>
            <h4 className="text-xs font-bold uppercase tracking-wider text-[#929BA9] mb-3">
              Compliance & Safety
            </h4>
            <ul className="space-y-2 text-sm">
              <li>
                <Link href="/terms" className="text-[#647084] hover:text-[#171C26] transition-colors">
                  Terms & Rehearsal Scope
                </Link>
              </li>
              <li>
                <a
                  href="https://sqlite.org/backup.html"
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1 text-[#647084] hover:text-[#171C26] transition-colors"
                >
                  <span>SQLite Online Backup API</span>
                  <ExternalLink className="w-3 h-3 text-[#929BA9]" />
                </a>
              </li>
              <li>
                <span className="text-xs text-[#929BA9]">Local-First • No Telemetry</span>
              </li>
            </ul>
          </div>
        </div>

        {/* Disclaimer & Copyright */}
        <div className="pt-8 border-t border-[#E5E9F0] flex flex-col md:flex-row items-center justify-between gap-4 text-xs text-[#929BA9]">
          <p>
            &copy; {new Date().getFullYear()} SchemaGuard. Engineered for deterministic schema reliability.
          </p>
          <p className="text-center md:text-right max-w-xl">
            SchemaGuard is a rehearsal tool. Passing checks indicate verified contracts and invariants held in an isolated sandbox; they do not guarantee absolute safety. Always review reports before applying to production.
          </p>
        </div>
      </div>
    </footer>
  );
}
