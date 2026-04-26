import type { Dispatch, SetStateAction } from 'react';


export type MoodLabel = 'calm' | 'energized' | 'happy' | 'sad' | 'intense' | 'chill';

export interface CuratedTrack {
  mbid: string;
  title: string | null;
  artist: string | null;
  genre: string;
  genre_tags: string[];
  mood: MoodLabel;
  bpm: number | null;
  key: string | null;
  scale: string | null;
}

export interface PlaylistTrack {
  position: number;
  mbid: string;
  title: string | null;
  artist: string | null;
  bpm: number | null;
  key: string | null;
  scale: string | null;
}

export interface Transition {
  from_mbid: string;
  to_mbid: string;
  probability: number;
  is_compatible: boolean;
  components: Record<string, number>;
}

export interface PlaylistResponse {
  tracks: PlaylistTrack[];
  transitions: Transition[];
  summary: string | null;
  average_compatibility: number;
  constraints: Array<{ name: string; satisfied: boolean; score: number }>;
}

export interface DemoState {
  selectedGenres: string[];
  selectedArtists: string[];
  startMood: MoodLabel | null;
  endMood: MoodLabel | null;
  startTrack: CuratedTrack | null;
  endTrack: CuratedTrack | null;
  playlist: PlaylistResponse | null;
  isLoading: boolean;
  error: string | null;
}

export const INITIAL_DEMO_STATE: DemoState = {
  selectedGenres: [],
  selectedArtists: [],
  startMood: null,
  endMood: null,
  startTrack: null,
  endTrack: null,
  playlist: null,
  isLoading: false,
  error: null,
};

export interface DemoSlideProps {
  isActive: boolean;
  replayKey: number;
  demoState: DemoState;
  setDemoState: Dispatch<SetStateAction<DemoState>>;
  onNext?: () => void;
}
