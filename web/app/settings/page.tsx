"use client";

import { Moon, Sun } from "lucide-react";
import { PageHeader } from "@/components/layout/page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useTheme } from "@/providers/theme-provider";

export default function SettingsPage() {
  const { theme, setTheme } = useTheme();
  return (
    <>
      <PageHeader title="Settings" description="Appearance and preferences." />
      <Card className="max-w-lg">
        <CardHeader>
          <CardTitle>Appearance</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-sm text-muted-foreground">
            Athena is dark-mode first. Choose your preferred theme.
          </p>
          <div className="flex gap-2">
            <Button
              variant={theme === "dark" ? "default" : "outline"}
              onClick={() => setTheme("dark")}
            >
              <Moon className="h-4 w-4" /> Dark
            </Button>
            <Button
              variant={theme === "light" ? "default" : "outline"}
              onClick={() => setTheme("light")}
            >
              <Sun className="h-4 w-4" /> Light
            </Button>
          </div>
        </CardContent>
      </Card>
    </>
  );
}
