import { apiRequest } from "@/lib/api-client";
import type { Page, PortfolioResponse } from "@/types/api";

export const portfolioService = {
  list: (params: { limit?: number; offset?: number } = {}) => {
    const q = new URLSearchParams();
    q.set("limit", String(params.limit ?? 20));
    q.set("offset", String(params.offset ?? 0));
    return apiRequest<Page<PortfolioResponse>>(`/portfolios?${q.toString()}`);
  },
  get: (id: string) => apiRequest<PortfolioResponse>(`/portfolios/${id}`),
};
