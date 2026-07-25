import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
});

export const metadata: Metadata = {
  title: "BOLA-Sentinel — API Authorization Vulnerability Detector",
  description:
    "Enterprise-grade BOLA/IDOR vulnerability detection engine combining static analysis, LLM reasoning, and dynamic verification.",
  keywords: [
    "BOLA",
    "IDOR",
    "API Security",
    "vulnerability detection",
    "static analysis",
    "LLM",
  ],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.variable} font-sans antialiased`}>
        {children}
      </body>
    </html>
  );
}
