"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Shield, GitBranch } from "lucide-react";

const NAV = [
  { href: "/", label: "Home" },
  { href: "/rehearsal", label: "Rehearsal" },
];

export default function Navbar() {
  const path = usePathname();

  return (
    <header className="sticky top-0 z-50 glass-nav">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-14 flex items-center justify-between">
        {/* Logo */}
        <Link href="/" className="flex items-center gap-2.5 group">
          <div className="w-7 h-7 rounded-lg bg-[#2563EB] flex items-center justify-center shadow-sm">
            <Shield className="w-4 h-4 text-white" strokeWidth={2.2} />
          </div>
          <span className="text-sm font-bold text-[#171C26] tracking-tight">SchemaGuard</span>
        </Link>

        {/* Nav links */}
        <nav className="hidden sm:flex items-center gap-1">
          {NAV.map((n) => (
            <Link
              key={n.href}
              href={n.href}
              className={`px-3.5 py-1.5 text-sm font-medium rounded-lg transition-colors ${
                path === n.href
                  ? "bg-[#2563EB]/10 text-[#2563EB]"
                  : "text-[#647084] hover:text-[#171C26] hover:bg-[#F1F4F8]"
              }`}
            >
              {n.label}
            </Link>
          ))}
        </nav>

        {/* Right actions */}
        <div className="flex items-center gap-2">
          <a
            href="https://github.com"
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-[#647084] hover:text-[#171C26] hover:bg-[#F1F4F8] rounded-lg transition-colors"
          >
            <GitBranch className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">GitHub</span>
          </a>
          <Link
            href="/rehearsal"
            className="btn-primary text-xs px-4 py-2"
          >
            Start Rehearsal
          </Link>
        </div>
      </div>
    </header>
  );
}
