import Link from "next/link";
import { Shield } from "lucide-react";

export default function Footer() {
  return (
    <footer className="border-t border-[#E5E9F0] bg-white mt-auto">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          <div className="w-5 h-5 rounded-md bg-[#2563EB] flex items-center justify-center">
            <Shield className="w-3 h-3 text-white" strokeWidth={2.2} />
          </div>
          <span className="text-xs font-semibold text-[#171C26]">SchemaGuard</span>
          <span className="text-xs text-[#929BA9]">— SQLite migration safety engine</span>
        </div>
        <nav className="flex items-center gap-4 text-xs text-[#647084]">
          <Link href="/" className="hover:text-[#171C26] transition-colors">Home</Link>
          <Link href="/rehearsal" className="hover:text-[#171C26] transition-colors">Rehearsal</Link>
          <Link href="/terms" className="hover:text-[#171C26] transition-colors">Terms</Link>
        </nav>
        <p className="text-xs text-[#929BA9]">
          &copy; {new Date().getFullYear()} SchemaGuard. Local-first. Zero production writes.
        </p>
      </div>
    </footer>
  );
}
