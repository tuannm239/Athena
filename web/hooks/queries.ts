"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { decisionsService } from "@/services/decisions";
import { portfolioService } from "@/services/portfolio";
import { companiesService, marketService } from "@/services/market";
import { opsService } from "@/services/ops";
import type { DecisionStatus } from "@/types/api";

export function useDecisions(params: { limit?: number; offset?: number; status?: DecisionStatus } = {}) {
  return useQuery({
    queryKey: ["decisions", params],
    queryFn: () => decisionsService.list(params),
  });
}

export function useDecision(id: string) {
  return useQuery({
    queryKey: ["decision", id],
    queryFn: () => decisionsService.get(id),
    enabled: !!id,
  });
}

export function useReviewDecision(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (vars: { outcome: "APPROVED" | "REJECTED"; note: string }) =>
      decisionsService.review(id, vars.outcome, vars.note),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["decision", id] });
      void qc.invalidateQueries({ queryKey: ["decisions"] });
    },
  });
}

export function usePortfolios(params: { limit?: number; offset?: number } = {}) {
  return useQuery({ queryKey: ["portfolios", params], queryFn: () => portfolioService.list(params) });
}

export function useMarketContext() {
  return useQuery({ queryKey: ["market-context"], queryFn: () => marketService.context() });
}

export function useCompany(ticker: string) {
  return useQuery({
    queryKey: ["company", ticker],
    queryFn: () => companiesService.get(ticker),
    enabled: !!ticker,
  });
}

export function useHealth() {
  return useQuery({ queryKey: ["health"], queryFn: () => opsService.health(), refetchInterval: 30_000 });
}
