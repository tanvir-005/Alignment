"use client";

import { useCallback } from "react";
import { api } from "@/lib/api";
import { statusLabel } from "@/lib/format";
import { useToast } from "@/components/ui/Toast";

/**
 * Optimistic status change for a list of todos held in React state.
 * `setTodos` receives an updater function (prev => next).
 */
export function useMoveTodo(setTodos, onDone) {
  const toast = useToast();

  return useCallback(
    async (todo, status) => {
      if (todo.status === status) return;
      const previous = todo.status;
      setTodos((list) => list.map((t) => (t.id === todo.id ? { ...t, status } : t)));
      try {
        const updated = await api(`/todos/${todo.id}/status`, { method: "PATCH", body: { status } });
        setTodos((list) => list.map((t) => (t.id === todo.id ? updated : t)));
        toast.success(`“${todo.title}” moved to ${statusLabel(status)}.`);
        onDone?.(updated);
      } catch (error) {
        setTodos((list) => list.map((t) => (t.id === todo.id ? { ...t, status: previous } : t)));
        toast.error(error.message);
      }
    },
    [setTodos, onDone, toast]
  );
}
