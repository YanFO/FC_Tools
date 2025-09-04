import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "投資助理 - AI 智能投資顧問",
  description: "提供股票查詢、新聞分析、總經數據和客戶管理的智能投資助理平台",
};

function Navigation() {
  return (
    <nav className="border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container mx-auto px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-6">
            <Link href="/dashboard" className="text-xl font-bold text-foreground">
              投資助理
            </Link>
            <div className="flex space-x-4">
              <Link
                href="/dashboard"
                className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
              >
                儀表板
              </Link>
              <Link
                href="/customers"
                className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
              >
                客戶管理
              </Link>
            </div>
          </div>
          <div className="text-sm text-muted-foreground">
            AI 智能投資顧問 v1.0
          </div>
        </div>
      </div>
    </nav>
  );
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-TW">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased min-h-screen bg-background`}
      >
        <Navigation />
        <main className="flex-1">
          {children}
        </main>
      </body>
    </html>
  );
}
