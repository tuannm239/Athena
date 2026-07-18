"use client";

import { PageHeader } from "@/components/layout/page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Stat } from "@/components/ui/stat";
import { useAuthStore } from "@/stores/auth-store";

export default function ProfilePage() {
  const user = useAuthStore((s) => s.user);
  if (!user) return null;
  return (
    <>
      <PageHeader title="Profile" description="Your Athena account." />
      <Card className="max-w-lg">
        <CardHeader>
          <CardTitle>Account</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <Stat label="Email" value={<span className="text-base">{user.email}</span>} />
            <Stat label="Role" value={<Badge variant="primary">{user.role}</Badge>} />
            <Stat label="Status" value={<Badge variant="gain">{user.status}</Badge>} />
          </div>
          <p className="text-xs text-muted-foreground">
            Password change and 2FA enrolment require backend endpoints not yet exposed. RBAC is
            enforced server-side on every request.
          </p>
        </CardContent>
      </Card>
    </>
  );
}
