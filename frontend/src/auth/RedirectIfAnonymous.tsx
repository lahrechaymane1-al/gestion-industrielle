import { useEffect } from "react";
import type { AxiosError } from "axios";
import { useAuth } from "./AuthContext";

/**
 * If the SPA shell loaded but the session is not authenticated (e.g. stale tab,
 * or edge cases where /api/auth/me returns 401/403), send the browser to Django login.
 * On hard /api/auth/me failures with 401/403, redirect as well (avoids a blank shell).
 */
export function RedirectIfAnonymous() {
  const { me, isLoading, isError, error } = useAuth();

  useEffect(() => {
    if (isLoading) return;
    if (me?.authenticated === false) {
      window.location.replace("/login/");
      return;
    }
    if (isError) {
      const status = (error as AxiosError | undefined)?.response?.status;
      if (status === 401 || status === 403) {
        window.location.replace("/login/");
      }
    }
  }, [isLoading, me?.authenticated, isError, error]);

  return null;
}