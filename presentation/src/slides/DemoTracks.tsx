import { useEffect } from "react";
import type { DemoSlideProps, CuratedTrack, MoodLabel } from "./demo-types";
import { T } from "../theme";
import playlistJson from "../data/playlist.json";

const MOOD_COLORS: Record<MoodLabel, string> = {
  calm: "#60a5fa",
  chill: "#2dd4bf",
  happy: "#facc15",
  sad: "#a78bfa",
  energized: "#fb923c",
  intense: "#f87171",
};

const ALBUM_ART: Record<string, string> = {
  "0e5f1add-c943-49a0-b824-169e7f7b82da": "/gjwhf.jpg",
  "d3528f95-1a3f-45d2-a569-826740c0adee": "/cn.png",
};

const MOODS: Record<string, MoodLabel> = {
  "0e5f1add-c943-49a0-b824-169e7f7b82da": "energized",
  "d3528f95-1a3f-45d2-a569-826740c0adee": "chill",
};

const { tracks } = playlistJson;
const first = tracks[0];
const last = tracks[tracks.length - 1];

function toState(t: typeof first): CuratedTrack {
  return {
    mbid: t.mbid,
    title: t.title,
    artist: t.artist,
    bpm: t.bpm,
    key: t.key,
    scale: t.scale,
    genre: "",
    genre_tags: [],
    mood: MOODS[t.mbid] ?? "calm",
  };
}

const START_TRACK = toState(first);
const END_TRACK = toState(last);

export function DemoTracks({ isActive, setDemoState, onNext }: DemoSlideProps) {
  useEffect(() => {
    if (!isActive) return;
    setDemoState((s) => ({
      ...s,
      startTrack: START_TRACK,
      endTrack: END_TRACK,
      playlist: null,
      isLoading: false,
      error: null,
    }));
  }, [isActive]);

  return (
    <div className={`slide ${isActive ? "active" : ""}`}>
      <h2 className="slide-title">From One Song to Another</h2>
      <p className="slide-subtitle">
        Wave Guide finds a path between any two tracks
      </p>

      <div
        style={{
          position: "absolute",
          top: 155,
          left: T.MARGIN,
          right: T.MARGIN,
          bottom: 100,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          gap: 48,
        }}
      >
        <TrackCard track={START_TRACK} label="Start" />
        <span style={{ fontSize: 48, color: T.MUTED }}>→</span>
        <TrackCard track={END_TRACK} label="End" />
      </div>

      <button
        className="btn"
        onClick={() => onNext?.()}
        style={{
          position: "absolute",
          bottom: 28,
          right: T.MARGIN,
          padding: "10px 28px",
          fontSize: 15,
          fontWeight: "bold",
          background: T.ORANGE,
          color: "#fff",
          borderColor: T.ORANGE,
        }}
      >
        Generate Playlist →
      </button>
    </div>
  );
}

function TrackCard({ track, label }: { track: CuratedTrack; label: string }) {
  const art = ALBUM_ART[track.mbid];
  const moodColor = MOOD_COLORS[track.mood];

  return (
    <div
      className="card"
      style={{ padding: "28px 36px", textAlign: "center", minWidth: 280 }}
    >
      <p
        style={{
          fontSize: 11,
          color: T.MUTED,
          fontStyle: "italic",
          marginBottom: 16,
          textTransform: "uppercase",
          letterSpacing: "0.08em",
        }}
      >
        {label}
      </p>

      {art && (
        <img
          src={art}
          alt={track.title ?? ""}
          style={{
            width: 140,
            height: 140,
            objectFit: "cover",
            borderRadius: 8,
            border: `1.5px solid ${T.BORDER}`,
            marginBottom: 16,
            display: "block",
            marginLeft: "auto",
            marginRight: "auto",
          }}
        />
      )}

      <p style={{ fontSize: 20, fontWeight: "bold", marginBottom: 4 }}>
        {track.title ?? "Unknown"}
      </p>
      <p style={{ fontSize: 14, color: T.MUTED, marginBottom: 14 }}>
        {track.artist ?? ""}
      </p>

      <div
        style={{
          display: "flex",
          justifyContent: "center",
          gap: 12,
          marginBottom: 14,
        }}
      >
        {track.bpm != null && (
          <span style={{ fontSize: 12, color: T.MUTED }}>
            {Math.round(track.bpm)} BPM
          </span>
        )}
        {track.key && (
          <span style={{ fontSize: 12, color: T.MUTED }}>
            {track.key} {track.scale}
          </span>
        )}
      </div>

      <span
        style={{
          display: "inline-block",
          fontSize: 12,
          fontWeight: "bold",
          textTransform: "capitalize",
          color: moodColor,
          background: `${moodColor}18`,
          border: `1px solid ${moodColor}40`,
          borderRadius: 20,
          padding: "3px 12px",
        }}
      >
        {track.mood}
      </span>
    </div>
  );
}
