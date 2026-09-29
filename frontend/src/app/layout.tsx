import type { Metadata } from "next";
import localFont from "next/font/local";
import "./globals.css";
import { Sidebar } from "@/components/layout/Sidebar";

const geistSans = localFont({
  src: "./fonts/GeistVF.woff",
  variable: "--font-geist-sans",
  weight: "100 900",
});
const geistMono = localFont({
  src: "./fonts/GeistMonoVF.woff",
  variable: "--font-geist-mono",
  weight: "100 900",
});

export const metadata: Metadata = {
  title: "Pravah (प्रवाह) | Baghewala Heavy Oil Digital Twin (SIH-26120)",
  description: "Pravah (प्रवाह): Real-time Well-to-Surface Digital Twin for Cyclic Steam Stimulation & Sucker Rod Pump Operations — Baghewala Field, Oil India Ltd.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${geistSans.variable} ${geistMono.variable} antialiased bg-black text-zinc-300 flex`}>
        <Sidebar />
        <div className="flex-1 min-h-screen overflow-x-hidden">
          {children}
        </div>
      </body>
    </html>
  );
}
