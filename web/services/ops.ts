import type { HealthFull } from "@/types/api";

/** /health/full is outside the /api/v1 envelope; fetch it directly. */
export const opsService = {
  health: async (): Promise<HealthFull> => {
    const res = await fetch("/api/health/full");
    if (!res.ok) throw new Error(`health ${res.status}`);
    return (await res.json()) as HealthFull;
  },
};
