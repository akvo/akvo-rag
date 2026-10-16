import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import "highlight.js/styles/github.css";
import { Toaster } from "@/components/ui/toaster";
import { UserProvider } from "@/contexts/userContext";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Akvo RAG",
  description: "Intelligent Dialogue & Document Retrieval Platform by Akvo",
  icons: {
    icon: [
      { url: "/favicon.ico" },
      { url: "/logo.svg", type: "image/svg+xml" },
    ],
    apple: [{ url: "/logo.png" }],
  },
};

export const dynamic = 'force-dynamic';

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <UserProvider>
          {children}
          <Toaster />
        </UserProvider>
      </body>
    </html>
  );
}
