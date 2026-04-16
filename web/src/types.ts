export interface ArtistCredit {
  name: string;
  joinphrase: string;
}

export interface Recording {
  id: string;
  title: string;
  length: number | null;
  "artist-credit"?: ArtistCredit[];
  "first-release-date"?: string;
}

export interface SearchResponse {
  recordings: Recording[];
  count: number;
}

export interface CompareComponents {
  key: number;
  tempo: number;
  energy: number;
  loudness: number;
  mood: number;
  timbre: number;
  genre: number;
}

export interface CompareResponse {
  recording_id_1: string;
  recording_id_2: string;
  score: number;
  is_compatible: boolean;
  components: CompareComponents;
  violations: string[];
  explanation: string;
}

export type MoodLabel =
  | "calm"
  | "energized"
  | "happy"
  | "sad"
  | "intense"
  | "chill";

export type InputMode = "track" | "mood";

export interface TrackInfo {
  position: number;
  mbid: string;
  title: string | null;
  artist: string | null;
  album: string | null;
  bpm: number | null;
  key: string | null;
  scale: string | null;
  energy?: number | null;
  mood_label?: MoodLabel | null;
  mood_confidence?: number | null;
}

export interface TransitionInfo {
  from_mbid: string;
  to_mbid: string;
  probability: number;
  penalty: number;
  is_compatible: boolean;
  components: CompareComponents;
  violations: string[];
}

export interface PlaylistResponse {
  source_mbid: string | null;
  source_mood?: MoodLabel | null;
  dest_mbid: string | null;
  dest_mood?: MoodLabel | null;
  requested_length: number;
  actual_length: number;
  total_cost: number;
  average_compatibility: number;
  tracks: TrackInfo[];
  transitions: TransitionInfo[];
  summary?: string;
  constraints?: Array<{ name: string; satisfied: boolean; score: number }>;
  quality?: Record<string, number>;
  error?: string;
  details?: string;
}

export type TabType = "compare" | "playlist";

export const COMPONENT_LABELS: Record<keyof CompareComponents, string> = {
  key: "Key",
  tempo: "Tempo",
  energy: "Energy",
  loudness: "Loudness",
  mood: "Mood",
  timbre: "Timbre",
  genre: "Genre",
};
