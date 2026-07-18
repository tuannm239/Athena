import Link from "next/link";
import { Button } from "@/components/ui/button";

export default function NotFound() {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-24 text-center">
      <p className="text-4xl font-bold">404</p>
      <p className="text-muted-foreground">This page could not be found.</p>
      <Link href="/"><Button variant="outline">Back to Dashboard</Button></Link>
    </div>
  );
}
