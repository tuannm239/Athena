"use client";

import { useMemo } from "react";
import Link from "next/link";
import { Network } from "lucide-react";
import { PageHeader } from "@/components/layout/page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Stat } from "@/components/ui/stat";
import { EmptyState } from "@/components/ui/empty-state";
import { BarList } from "@/components/ui/bar-list";
import { useDecisions } from "@/hooks/queries";

export default function KnowledgeGraphPage() {
  const decisions = useDecisions({ limit: 100 });
  const items = useMemo(() => decisions.data?.items ?? [], [decisions.data]);

  const graph = useMemo(() => {
    const categoryCount = new Map<string, number>();
    const sourceCount = new Map<string, number>();
    let edges = 0;
    for (const d of items) {
      for (const e of d.evidence) {
        edges += 1;
        categoryCount.set(e.category, (categoryCount.get(e.category) ?? 0) + 1);
        sourceCount.set(e.source, (sourceCount.get(e.source) ?? 0) + 1);
      }
    }
    const nodes = items.length + categoryCount.size + sourceCount.size;
    const topCategories = [...categoryCount.entries()]
      .sort((a, b) => b[1] - a[1])
      .slice(0, 8)
      .map(([label, value]) => ({ label, value }));
    return { nodes, edges, decisions: items.length, categories: categoryCount.size, topCategories };
  }, [items]);

  return (
    <>
      <PageHeader
        title="Knowledge Graph"
        description="The live graph of your decisions and the evidence that supports them (RFC-0019). Nodes and edges are built from real decision data."
      />

      {decisions.isLoading ? (
        <Skeleton className="h-64 w-full" />
      ) : items.length === 0 ? (
        <EmptyState
          icon={Network}
          title="No graph yet"
          description="As decisions gather evidence, their entities and links appear here."
        />
      ) : (
        <>
          <div className="mb-4 grid grid-cols-2 gap-4 md:grid-cols-4">
            <Card>
              <CardContent className="p-4">
                <Stat label="Nodes" value={graph.nodes} />
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4">
                <Stat label="Edges" value={graph.edges} />
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4">
                <Stat label="Decisions" value={graph.decisions} />
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4">
                <Stat label="Evidence categories" value={graph.categories} />
              </CardContent>
            </Card>
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Top evidence categories</CardTitle>
              </CardHeader>
              <CardContent>
                <BarList
                  data={graph.topCategories.map((c) => ({ ...c, tone: "primary" as const }))}
                />
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Decision → evidence links</CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="max-h-80 space-y-2 overflow-y-auto text-sm">
                  {items.slice(0, 20).map((d) => (
                    <li key={d.id} className="rounded-md border p-2">
                      <Link href={`/decisions/${d.id}`} className="font-medium hover:underline">
                        {d.hypothesis}
                      </Link>
                      <div className="mt-1 flex flex-wrap gap-1">
                        {d.evidence.length === 0 ? (
                          <span className="text-xs text-muted-foreground">no evidence linked</span>
                        ) : (
                          d.evidence.slice(0, 6).map((e) => (
                            <Badge
                              key={e.id}
                              variant={
                                e.direction === "SUPPORTING"
                                  ? "gain"
                                  : e.direction === "CONTRADICTING"
                                    ? "loss"
                                    : "muted"
                              }
                            >
                              {e.category}
                            </Badge>
                          ))
                        )}
                      </div>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          </div>
        </>
      )}
    </>
  );
}
