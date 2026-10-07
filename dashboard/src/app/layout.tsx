import type { Metadata } from "next";
import "./globals.css";
import { loadDashboardData } from "@/lib/state";

export function generateMetadata(): Metadata {
  const data = loadDashboardData();
  return {
    title: `${data.project.name} — open research control plane`,
    description:
      "Live, capability-based progress for an open research program teaching multimodal AI to read ancient Egyptian Hieratic handwriting.",
    openGraph: {
      title: `${data.project.name} — open research control plane`,
      description: "Capability-weighted progress, task graph, and research activity, derived from the public repository.",
      type: "website",
    },
  };
}

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <head>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <meta name="theme-color" content="#f6f4ef" />
      </head>
      <body>{children}</body>
    </html>
  );
}
