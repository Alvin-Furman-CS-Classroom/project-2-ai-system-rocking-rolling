import { useMutation } from "@tanstack/react-query";
import type { MoodLabel, PlaylistResponse } from "../types";

export interface PlaylistParams {
  sourceId?: string;
  sourceMood?: MoodLabel;
  destId?: string;
  destMood?: MoodLabel;
  length: number;
  beamWidth: number;
}

export function usePlaylistGenerator() {
  return useMutation<PlaylistResponse, Error, PlaylistParams>({
    mutationFn: async ({
      sourceId,
      sourceMood,
      destId,
      destMood,
      length,
      beamWidth,
    }) => {
      const params = new URLSearchParams({
        length: length.toString(),
        beam_width: beamWidth.toString(),
      });

      if (sourceId) params.set("source_mbid", sourceId);
      else if (sourceMood) params.set("source_mood", sourceMood);

      if (destId) params.set("dest_mbid", destId);
      else if (destMood) params.set("dest_mood", destMood);

      const res = await fetch(`/api/playlist?${params}`);
      if (!res.ok) {
        const body = await res.json().catch(() => null);
        throw new Error(body?.error ?? `API error: ${res.status}`);
      }
      return res.json();
    },
  });
}
