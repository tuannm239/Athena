import type { Metadata, Viewport } from "next";
import "./globals.css";
import { QueryProvider } from "@/providers/query-provider";
import { ThemeProvider } from "@/providers/theme-provider";
import { AuthProvider } from "@/providers/auth-provider";
import { AppShell } from "@/components/layout/app-shell";
import { PwaRegister } from "@/components/pwa-register";
import { Toaster } from "@/components/ui/toaster";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";

export const metadata: Metadata = {
  title: { default: "Athena — Decision Intelligence", template: "%s · Athena" },
  description:
    "Athena Financial Decision Intelligence Platform — explainable, probabilistic, risk-aware investment decisions with mandatory human approval.",
  applicationName: "Athena",
  manifest: "/manifest.webmanifest",
  appleWebApp: { capable: true, statusBarStyle: "black-translucent", title: "Athena" },
};

export const viewport: Viewport = {
  themeColor: "#0b0f19",
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>
        <a
          href="#main"
          className="sr-only focus:not-sr-only focus:absolute focus:z-50 focus:m-2 focus:rounded focus:bg-primary focus:px-3 focus:py-2 focus:text-primary-foreground"
        >
          Skip to content
        </a>
        <ThemeProvider>
          <QueryProvider>
            <AuthProvider>
              <AppShell>
                <div id="main">{children}</div>
              </AppShell>
              <Toaster />
              <ConfirmDialog />
            </AuthProvider>
          </QueryProvider>
        </ThemeProvider>
        <PwaRegister />
      </body>
    </html>
  );
}
