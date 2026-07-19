"use client";

/**
 * Reusable research-notes panel (Phase 8). Add notes, attach files
 * (PDF/Excel/annual reports — small files stored inline, larger kept as
 * metadata), mark human-reviewed, and view the audit trail. Scoped to a
 * company ticker and/or decision when provided. Client-side persistence.
 */
import { useRef, useState } from "react";
import { CheckCircle2, Circle, FileText, Paperclip, Plus, Trash2 } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { useNotesStore, MAX_INLINE_BYTES, newId, type Attachment } from "@/stores/notes-store";
import { formatDateTime } from "@/lib/utils";

export function NotesPanel({ ticker, decisionId }: { ticker?: string; decisionId?: string }) {
  const notes = useNotesStore((s) =>
    s.notes.filter(
      (n) => (!ticker || n.ticker === ticker) && (!decisionId || n.decisionId === decisionId),
    ),
  );
  const add = useNotesStore((s) => s.add);
  const remove = useNotesStore((s) => s.remove);
  const toggleReviewed = useNotesStore((s) => s.toggleReviewed);
  const addAttachment = useNotesStore((s) => s.addAttachment);

  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const fileFor = useRef<Record<string, HTMLInputElement | null>>({});

  function submit() {
    if (!title.trim()) return;
    add({ title: title.trim(), body: body.trim(), ticker, decisionId });
    setTitle("");
    setBody("");
  }

  async function onFile(noteId: string, file: File) {
    const att: Attachment = {
      id: newId(),
      name: file.name,
      kind: file.type || file.name.split(".").pop() || "file",
      size: file.size,
    };
    if (file.size <= MAX_INLINE_BYTES) {
      att.dataUrl = await new Promise<string>((resolve) => {
        const reader = new FileReader();
        reader.onload = () => resolve(String(reader.result));
        reader.readAsDataURL(file);
      });
    }
    addAttachment(noteId, att);
  }

  return (
    <div className="space-y-3">
      <Card>
        <CardContent className="space-y-2 p-4">
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Note title (e.g. Q3 earnings takeaways)"
            className="h-9 w-full rounded-md border bg-background px-3 text-sm"
            aria-label="Note title"
          />
          <textarea
            value={body}
            onChange={(e) => setBody(e.target.value)}
            placeholder="Your research notes…"
            rows={3}
            className="w-full rounded-md border bg-background px-3 py-2 text-sm"
            aria-label="Note body"
          />
          <div className="flex justify-end">
            <Button size="sm" onClick={submit} disabled={!title.trim()}>
              <Plus className="h-3.5 w-3.5" /> Add note
            </Button>
          </div>
        </CardContent>
      </Card>

      {notes.length === 0 ? (
        <EmptyState
          icon={FileText}
          title="No notes yet"
          description="Add a note above and attach PDFs, Excel files or annual reports."
        />
      ) : (
        notes.map((n) => (
          <Card key={n.id}>
            <CardContent className="p-4">
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <p className="flex items-center gap-2 font-medium">
                    {n.title}
                    {n.reviewed ? <Badge variant="gain">reviewed</Badge> : null}
                    {n.ticker ? <Badge variant="muted">{n.ticker}</Badge> : null}
                  </p>
                  {n.body ? <p className="mt-1 text-sm text-muted-foreground">{n.body}</p> : null}
                </div>
                <div className="flex shrink-0 items-center gap-1">
                  <button
                    onClick={() => toggleReviewed(n.id)}
                    aria-label={n.reviewed ? "Clear review" : "Mark reviewed"}
                    title={n.reviewed ? "Clear review" : "Mark reviewed (human review)"}
                    className="rounded p-1 hover:bg-accent"
                  >
                    {n.reviewed ? (
                      <CheckCircle2 className="h-4 w-4 text-gain" />
                    ) : (
                      <Circle className="h-4 w-4 text-muted-foreground" />
                    )}
                  </button>
                  <button
                    onClick={() => fileFor.current[n.id]?.click()}
                    aria-label="Attach file"
                    title="Attach PDF / Excel / annual report"
                    className="rounded p-1 hover:bg-accent"
                  >
                    <Paperclip className="h-4 w-4 text-muted-foreground" />
                  </button>
                  <input
                    ref={(el) => {
                      fileFor.current[n.id] = el;
                    }}
                    type="file"
                    accept=".pdf,.xlsx,.xls,.csv,.doc,.docx"
                    className="hidden"
                    onChange={(e) => {
                      const f = e.target.files?.[0];
                      if (f) void onFile(n.id, f);
                      e.target.value = "";
                    }}
                  />
                  <button
                    onClick={() => remove(n.id)}
                    aria-label="Delete note"
                    className="rounded p-1 text-muted-foreground hover:text-loss"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </div>

              {n.attachments.length > 0 ? (
                <ul className="mt-2 space-y-1">
                  {n.attachments.map((a) => (
                    <li key={a.id} className="flex items-center gap-2 text-xs">
                      <Paperclip className="h-3 w-3 text-muted-foreground" />
                      {a.dataUrl ? (
                        <a href={a.dataUrl} download={a.name} className="text-primary hover:underline">
                          {a.name}
                        </a>
                      ) : (
                        <span>{a.name}</span>
                      )}
                      <span className="text-muted-foreground">({(a.size / 1024).toFixed(0)} KB)</span>
                    </li>
                  ))}
                </ul>
              ) : null}

              <details className="mt-2">
                <summary className="cursor-pointer text-xs text-muted-foreground">
                  Audit trail ({n.audit.length})
                </summary>
                <ul className="mt-1 space-y-0.5 text-[11px] text-muted-foreground">
                  {n.audit.map((a, i) => (
                    <li key={i}>
                      {formatDateTime(new Date(a.at).toISOString())} — {a.action}
                    </li>
                  ))}
                </ul>
              </details>
            </CardContent>
          </Card>
        ))
      )}
    </div>
  );
}
