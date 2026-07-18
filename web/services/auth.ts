import { apiRequest } from "@/lib/api-client";
import type {
  ApiKeyCreatedResponse,
  ApiKeyResponse,
  TokenResponse,
  UserResponse,
} from "@/types/api";

export const authService = {
  login: (email: string, password: string) =>
    apiRequest<TokenResponse>("/auth/login", {
      method: "POST",
      body: { email, password },
      anonymous: true,
    }),

  register: (email: string, password: string) =>
    apiRequest<UserResponse>("/auth/register", {
      method: "POST",
      body: { email, password },
      anonymous: true,
    }),

  listApiKeys: () => apiRequest<ApiKeyResponse[]>("/auth/api-keys"),

  createApiKey: (name: string) =>
    apiRequest<ApiKeyCreatedResponse>("/auth/api-keys", { method: "POST", body: { name } }),

  revokeApiKey: (id: string) =>
    apiRequest<{ status: string }>(`/auth/api-keys/${id}`, { method: "DELETE" }),
};
