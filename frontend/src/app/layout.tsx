import type { Metadata } from "next";
import "./globals.css";
import { GovFooter, GovHeader } from "@/components/gov-chrome";
import { PrefsProvider } from "@/lib/prefs";

export const metadata: Metadata = {
  title: "SpecSure — Public Procurement Standards Compliance Portal (Prototype)",
  description:
    "Prototype for Smart India Hackathon 2026 (PS SIH26108): intent-to-tender generation with Indian Standards, QCO and amendment tracking, contractor bid matching, sealed evaluation with Make in India and MSE preference, and a tamper-evident audit trail. Not an official Government of India website.",
  icons: { icon: "/favicon.ico" },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        <link
          href="https://fonts.googleapis.com/css2?family=Noto+Sans:wght@400;500;600;700;800&family=Noto+Sans+Devanagari:wght@400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="bg-[#f3f6fa] text-[#0f2748] min-h-screen flex flex-col antialiased selection:bg-[#ff9933]/30">
        <PrefsProvider>
          <GovHeader />
          <main id="main" tabIndex={-1} className="flex-1 outline-none">
            {children}
          </main>
          <GovFooter />
        </PrefsProvider>
      </body>
    </html>
  );
}
