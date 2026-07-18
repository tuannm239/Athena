import { apiRequest } from "@/lib/api-client";
import type {
  DecisionCreateRequest,
  DecisionResponse,
  DecisionStatus,
  DecisionUpdateRequest,
  Page,
} from "@/types/api";

export const decisionsService = {
  list: (params: { limit?: number; offset?: number; status?: DecisionStatus } = {}) => {
    const q = new URLSearchParams();
    q.set("limit", String(params.limit ?? 20));
    q.set("offset", String(params.offset ?? 0));
    if (params.status) q.set("status", params.status);
    return apiRequest<Page<DecisionResponse>>(`/decisions?${q.toString()}`);
  },

  get: (id: string) => apiRequest<DecisionResponse>(`/decisions/${id}`),

  create: (body: DecisionCreateRequest) =>
    apiRequest<DecisionResponse>("/decisions", { method: "POST", body }),

  update: (id: string, body: DecisionUpdateRequest) =>
    apiRequest<DecisionResponse>(`/decisions/${id}`, { method: "PATCH", body }),

  review: (id: string, outcome: "APPROVED" | "REJECTED", note: string) =>
    apiRequest<DecisionResponse>(`/decisions/${id}`, {
      method: "PATCH",
      body: { status: outcome, review_note: note },
    }),
};
