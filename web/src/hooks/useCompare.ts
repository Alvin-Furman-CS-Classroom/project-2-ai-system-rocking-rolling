import { useMutation } from "@tanstack/react-query";
import type { CompareResponse } from "../types";

export function useCompare() {
  return useMutation<CompareResponse, Error, { id1: string; id2: string }>({
    mutationFn: async ({ id1, id2 }) => {
      const res = await fetch(
        `/api/compare?recording_id_1=${encodeURIComponent(id1)}&recording_id_2=${encodeURIComponent(id2)}`,
      );
      if (!res.ok) {
        const body = await res.json().catch(() => null);
        throw new Error(body?.error ?? `API error: ${res.status}`);
      }
      return res.json();
    },
  });
}
