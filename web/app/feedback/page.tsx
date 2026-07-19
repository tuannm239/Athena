"use client";

import { useState } from "react";
import { MessageSquare, Send } from "lucide-react";
import { PageHeader } from "@/components/layout/page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { toast } from "@/stores/toast-store";

type Category = "Bug" | "Idea" | "Data issue" | "Other";
const CATEGORIES: Category[] = ["Bug", "Idea", "Data issue", "Other"];

interface Submitted {
  category: Category;
  message: string;
  at: string;
}

const KEY = "athena-feedback";

function load(): Submitted[] {
  if (typeof window === "undefined") return [];
  try {
    return JSON.parse(window.localStorage.getItem(KEY) ?? "[]") as Submitted[];
  } catch {
    return [];
  }
}

export default function FeedbackPage() {
  const [category, setCategory] = useState<Category>("Idea");
  const [message, setMessage] = useState("");
  const [history, setHistory] = useState<Submitted[]>(load);

  function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!message.trim()) return;
    const entry: Submitted = { category, message: message.trim(), at: new Date().toISOString() };
    const next = [entry, ...history].slice(0, 50);
    setHistory(next);
    if (typeof window !== "undefined") window.localStorage.setItem(KEY, JSON.stringify(next));
    setMessage("");
    toast.success("Thanks — your feedback was recorded.");
  }

  return (
    <>
      <PageHeader
        title="Feedback"
        description="Tell us what's working and what isn't. Feedback is stored locally in this pilot and reviewed by the team."
      />

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <MessageSquare className="h-4 w-4" /> Send feedback
            </CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={submit} className="space-y-3">
              <div>
                <label className="mb-1 block text-xs text-muted-foreground">Category</label>
                <div className="flex flex-wrap gap-1">
                  {CATEGORIES.map((c) => (
                    <button
                      key={c}
                      type="button"
                      onClick={() => setCategory(c)}
                      className={`rounded-full border px-3 py-1 text-xs ${
                        category === c ? "bg-primary text-primary-foreground" : "hover:bg-accent"
                      }`}
                    >
                      {c}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <label htmlFor="msg" className="mb-1 block text-xs text-muted-foreground">
                  Message
                </label>
                <textarea
                  id="msg"
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  rows={5}
                  required
                  placeholder="What would you like to tell us?"
                  className="w-full rounded-md border bg-background px-3 py-2 text-sm"
                />
              </div>
              <div className="flex justify-end">
                <Button type="submit" disabled={!message.trim()}>
                  <Send className="h-3.5 w-3.5" /> Send feedback
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Your submissions</CardTitle>
          </CardHeader>
          <CardContent>
            {history.length === 0 ? (
              <p className="text-sm text-muted-foreground">No feedback submitted yet.</p>
            ) : (
              <ul className="space-y-2">
                {history.map((h, i) => (
                  <li key={i} className="rounded-md border p-2">
                    <div className="flex items-center justify-between">
                      <Badge variant="muted">{h.category}</Badge>
                      <span className="text-xs text-muted-foreground">
                        {new Date(h.at).toLocaleString()}
                      </span>
                    </div>
                    <p className="mt-1 text-sm">{h.message}</p>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      </div>
    </>
  );
}
