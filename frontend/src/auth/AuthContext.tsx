/* eslint-disable react-refresh/only-export-components -- Auth module exports hooks next to the provider. */
import { createContext, useCallback, useContext, useMemo, type ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import type { AxiosError } from "axios";
import { api } from "../api/client";
import { lockedShiftFromMe } from "./authSession";

export type MePayload = {
  authenticated: boolean;
  id?: number;
  identifiant?: string;
  role?: string;
  shift?: string | null;
  equipe?: string | null;
  effectif_id?: number | null;
  permissions?: {
    create?: boolean;
    read?: boolean;
    update?: boolean;
    delete?: boolean;
  };
};

type AuthContextValue = {
  me: MePayload | undefined;
  isLoading: boolean;
  isError: boolean;
  error: unknown;
  refetch: () => Promise<unknown>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["auth-me"],
    queryFn: async () => {
      try {
        const { data: res } = await api.get<MePayload>("/api/auth/me/");
        return res;
      } catch (e) {
        const status = (e as AxiosError).response?.status;
        if (status === 401 || status === 403) {
          return { authenticated: false } satisfies MePayload;
        }
        throw e;
      }
    },
    retry: false,
    staleTime: 30_000,
    refetchOnWindowFocus: true,
  });

  const refetchAuth = useCallback(async () => refetch(), [refetch]);

  const value = useMemo(
    () => ({
      me: data,
      isLoading,
      isError,
      error,
      refetch: refetchAuth,
    }),
    [data, isLoading, isError, error, refetchAuth]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth doit être utilisé dans AuthProvider");
  }
  return ctx;
}

export function useMe(): MePayload | undefined {
  return useAuth().me;
}

export function useIsPSP(): boolean {
  return useMe()?.role === "PSP";
}

/** Shift impose pour les formulaires PSP (Effectif). */
export function useLockedShift(): string | undefined {
  return lockedShiftFromMe(useMe());
}
