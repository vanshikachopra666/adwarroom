import type { Metadata } from "next";
import { Inter } from "next/font/google";

import "./globals.css";

const heading = Inter({ subsets: ["latin"], variable: "--font-heading", weight: ["500", "600", "700"] });
const body = Inter({ subsets: ["latin"], weight: ["400", "500", "600"], variable: "--font-body" });

export const metadata: Metadata = {
  title: "Competitor Ad War Room",
  description: "Competitive intelligence dashboard for ad creative and messaging analysis.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={`${heading.variable} ${body.variable} font-[var(--font-body)]`}>
        {children}
      </body>
    </html>
  );
}
