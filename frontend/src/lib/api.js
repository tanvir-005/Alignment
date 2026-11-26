"use client";

import { useCallback, useEffect, useRef, useState } from "react";

export class ApiError extends Error {
  constructor(message, status, data) {
    super(message);
    this.status = status;
    this.data = data;
  }
}

/**
 * Call the Next.js BFF (/api/...). Paths are given WITHOUT a trailing slash,
 * e.g. api("/todos?scope=mine"). The BFF adds the slash Django expects.
 */
export async function api(path, { method = "GET", body } = {}) {
  const response = await fetch(`/api${path}`, {
    method,
    headers: body !== undefined ? { "Content-Type": "application/json" } : undefined,
    body: body !== undefined ? JSON.stringify(body) : undefined,
    cache: "no-store",
  });

  if (response.status === 401 && typeof window !== "undefined") {
    window.location.href = "/login";
    throw new ApiError("Your session has expired.", 401);
  }

  let data = null;
  if (response.status !== 204) {
    try {
      data = await response.json();
    } catch {
      data = null;
    }
  }

  if (!response.ok) {
    throw new ApiError(data?.error || "Something went wrong. Please try again.", response.status, data);
  }
  return data;
}

/** Fetch on mount / whenever `path` changes. Pass null to skip. */
export function useFetch(path) {
  const [state, setState] = useState({ data: null, error: null, loading: Boolean(path) });
  const counter = useRef(0);

  const load = useCallback(
    async ({ silent = false } = {}) => {
      if (!path) return;
      const id = ++counter.current;
      if (!silent) setState((s) => ({ ...s, loading: true, error: null }));
      try {
        const data = await api(path);
        if (id === counter.current) setState({ data, error: null, loading: false });
      } catch (error) {
        if (id === counter.current) setState((s) => ({ data: silent ? s.data : null, error, loading: false }));
      }
    },
    [path]
  );

  useEffect(() => {
    load();
    const ref = counter;
    return () => {
      ref.current++; // invalidate in-flight requests on unmount / path change
    };
  }, [load]);

  const setData = useCallback(
    (updater) =>
      setState((s) => ({ ...s, data: typeof updater === "function" ? updater(s.data) : updater })),
    []
  );

  return { ...state, reload: load, setData };
}
