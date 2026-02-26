import { useQuery } from "@tanstack/react-query";
import { MusicBrainzClient } from "@kellnerd/musicbrainz";
import type { SearchResponse } from "../types";

const client = new MusicBrainzClient({
  app: { name: "SongSimilarity", version: "0.1.0" },
});

export function useRecordingSearch(query: string) {
  return useQuery<SearchResponse>({
    queryKey: ["recording-search", query],
    queryFn: async () => {
      const res = await client.get("recording", {
        query,
        limit: 10,
      });
      return res as SearchResponse;
    },
    enabled: query.length >= 2,
    staleTime: 5 * 60 * 1000,
  });
}
