import { useMutation } from "@tanstack/react-query";
import type { PlaylistResponse } from "../types";

export function usePlaylistGenerator() {
  return useMutation<
    PlaylistResponse,
    Error,
    { sourceId: string; destId: string; length: number; beamWidth: number }
  >({
    mutationFn: async ({ sourceId, destId, length, beamWidth }) => {
      const params = new URLSearchParams({
        source_mbid: sourceId,
        dest_mbid: destId,
        length: length.toString(),
        beam_width: beamWidth.toString(),
      });
      const res = await fetch(`/api/playlist?${params}`);
      if (!res.ok) {
        const body = await res.json().catch(() => null);
        throw new Error(body?.error ?? `API error: ${res.status}`);
      }
      return res.json();
    },
  });
}
