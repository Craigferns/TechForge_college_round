/**
 * API client: live HTTP by default; typed fixtures only when VITE_API_MODE=mock
 * (`npm run dev:mock`, tests). Mock mode is always announced in the UI (Navbar).
 */

import { useState, useEffect, useCallback } from "react";
import { resolveMockPath } from "../mocks";

export const API_MODE: "live" | "mock" = import.meta.env.VITE_API_MODE === "mock" ? "mock" : "live";
const API_BASE = import.meta.env.VITE_API_BASE || "/api/v1";

export async function apiClient<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const fullPath = endpoint.startsWith("/api") ? endpoint : `${API_BASE}${endpoint}`;

  if (API_MODE === "mock") {
    return resolveMockPath<T>(fullPath);
  }

  let response: Response;
  try {
    response = await fetch(fullPath, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...options?.headers,
      },
    });
  } catch {
    throw new Error("Cannot reach the AgentBreak API. Is the backend running on 127.0.0.1:8000?");
  }

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData?.error?.message || `HTTP ${response.status}: ${response.statusText}`);
  }

  return response.json();
}

export function useApi<T>(endpoint: string | null) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState<boolean>(endpoint !== null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!endpoint) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      setData(await apiClient<T>(endpoint));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }, [endpoint]);

  useEffect(() => {
    let active = true;
    if (!endpoint) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    apiClient<T>(endpoint)
      .then((res) => active && setData(res))
      .catch((err: unknown) => active && setError(err instanceof Error ? err.message : String(err)))
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [endpoint]);

  return { data, loading, error, refetch: load };
}

interface Listable {
  items: { id: string }[];
}

/**
 * Load `${collection}/${id}`, or the most recent record of the collection when no id is given.
 * `empty` is true when the collection has no records yet (first run).
 */
export function useByIdOrLatest<T>(collection: string, id: string | undefined, listQuery = "") {
  const latest = useApi<Listable>(id ? null : `${collection}?limit=1${listQuery}`);
  const resolvedId = id ?? latest.data?.items?.[0]?.id;
  const record = useApi<T>(resolvedId ? `${collection}/${resolvedId}` : null);
  return {
    data: record.data,
    id: resolvedId,
    loading: latest.loading || record.loading,
    error: latest.error || record.error,
    empty: !id && latest.data !== null && !latest.data.items?.length,
    refetch: record.refetch,
  };
}
