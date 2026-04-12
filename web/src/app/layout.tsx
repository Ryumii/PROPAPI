import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "PropAPI — 土地調査統合プラットフォーム",
  description:
    "住所を入力するだけで、ハザードリスク・都市計画規制・用途地域を一括で確認。",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ja">
      <body>{children}</body>
    </html>
  );
}
