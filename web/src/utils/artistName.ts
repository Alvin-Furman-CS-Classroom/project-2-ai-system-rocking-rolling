import type { Recording } from "../types";

export function artistName(recording: Recording): string {
  return (
    recording["artist-credit"]
      ?.map((c) => c.name + (c.joinphrase ?? ""))
      .join("") ?? "Unknown Artist"
  );
}
