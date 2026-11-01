import type { Metadata } from "next";
import "./globals.css";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";

export const metadata: Metadata = {
  title: "SchemaGuard — Database Migration Rehearsal & Verification",
  description:
    "Rehearse schema migrations in an isolated SQLite sandbox before touching production data. Replay application query contracts, evaluate invariants, and verify safety.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="h-full bg-[#F7F8FA]">
      <body className="min-h-full flex flex-col bg-[#F7F8FA] text-[#171C26] antialiased selection:bg-[#2563EB]/15 selection:text-[#2563EB]">
        <Navbar />
        <main className="flex-1">{children}</main>
        <Footer />
      </body>
    </html>
  );
}
