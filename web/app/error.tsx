"use client";
import { Button } from "@/components/ui/button";

export default function Error({ reset }: { error: Error; reset: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-24 text-center" role="alert">
      <p className="text-lg font-semibold">Something went wrong</p>
      <p className="text-sm text-muted-foreground">An unexpected error occurred while rendering this view.</p>
      <Button variant="outline" onClick={reset}>Try again</Button>
    </div>
  );
}
