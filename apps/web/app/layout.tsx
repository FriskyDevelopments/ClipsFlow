import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ClipsFlow",
  description: "Telegram-native clip processing and exports.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
