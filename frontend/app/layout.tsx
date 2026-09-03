import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AI Revenue Recovery Agent | Razorpay Track 03",
  description:
    "AI-powered revenue recovery system with Hinglish voice agent, deterministic policy engine, and real-time Razorpay payment recovery.",
  keywords: ["revenue recovery", "AI agent", "Razorpay", "payment recovery", "LiveKit"],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
      </head>
      <body style={{ background: '#0a0b0f', minHeight: '100vh' }}>
        {children}
      </body>
    </html>
  );
}
