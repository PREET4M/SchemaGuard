"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ShieldCheck, ArrowRight, Settings as SettingsIcon } from "lucide-react";

export default function Navbar() {
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-50 w-full glass-nav">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Left: Brand */}
        <Link href="/" className="flex items-center gap-2.5 group">
          <div className="w-8 h-8 rounded-lg bg-[#2563EB]/10 border border-[#2563EB]/25 flex items-center justify-center text-[#2563EB] group-hover:bg-[#2563EB] group-hover:text-white transition-colors duration-200">
            <ShieldCheck className="w-5 h-5 stroke-[2.2]" />
          </div>
          <div className="flex items-center gap-2">
            <span className="text-[17px] font-bold tracking-tight text-[#171C26]">
              SchemaGuard
            </span>
            <span className="text-[11px] font-semibold text-[#2563EB] bg-[#2563EB]/10 border border-[#2563EB]/20 px-2 py-0.5 rounded-md">
              v2.0
            </span>
          </div>
        </Link>

        {/* Center: Navigation Links */}
        <nav className="hidden md:flex items-center gap-8">
          <Link
            href="/#product"
            className="text-sm font-medium text-[#647084] hover:text-[#171C26] transition-colors"
          >
            Product
          </Link>
          <Link
            href="/#how-it-works"
            className="text-sm font-medium text-[#647084] hover:text-[#171C26] transition-colors"
          >
            How It Works
          </Link>
          <Link
            href="/#safety"
            className="text-sm font-medium text-[#647084] hover:text-[#171C26] transition-colors"
          >
            Safety
          </Link>
          <Link
            href="/settings"
            className={`text-sm font-medium transition-colors ${
              pathname === "/settings"
                ? "text-[#2563EB] font-semibold"
                : "text-[#647084] hover:text-[#171C26]"
            }`}
          >
            Settings
          </Link>
        </nav>

        {/* Right: Actions */}
        <div className="flex items-center gap-3">
          <Link
            href="/settings"
            className="md:hidden p-2 text-[#647084] hover:text-[#171C26] rounded-lg hover:bg-[#F1F4F8]"
            title="Settings"
          >
            <SettingsIcon className="w-5 h-5" />
          </Link>
          <Link
            href="/rehearsal"
            className="inline-flex items-center gap-2 px-4 py-2 text-sm font-semibold text-white bg-[#2563EB] hover:bg-[#1D4ED8] active:bg-[#1E40AF] rounded-lg shadow-sm hover:shadow transition-all duration-150"
          >
            <span>Start Rehearsal</span>
            <ArrowRight className="w-4 h-4 stroke-[2.2]" />
          </Link>
        </div>
      </div>
    </header>
  );
}
