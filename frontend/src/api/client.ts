/**
 * API client supporting both live HTTP backend and typed mock mode.
 */

import { useState, useEffect } from "react";
import { resolveMockPath } from "../mocks";

const API_MODE = import.meta.env.VITE_API_MODE || "mock";
const API_BASE = import.meta.env.VITE_API_BASE || "/api/v1";

export async function apiClient<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const fullPath = endpoint.startsWith("/api") ? endpoint : `${API_BASE}${endpoint}`;

  if (API_MODE === "mock") {
    return resolveMockPath<T>(fullPath);
  }

  const response = await fetch(fullPath, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData?.error?.message || `HTTP ${response.status}: ${response.statusText}`);
  }

  return response.json();
}

export function useApi<T>(endpoint: string | null) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!endpoint) {
      setLoading(false);
      return;
    }

    let active = true;
    setLoading(true);
    setError(null);

    apiClient<T>(endpoint)
      .then((res) => {
        if (active) {
          setData(res);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (active) {
          setError(err.message);
          setLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, [endpoint]);

  return { data, loading, error, refetch: () => apiClient<T>(endpoint!).then(setData) };
}
