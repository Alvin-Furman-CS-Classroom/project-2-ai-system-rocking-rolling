import { useEffect, useRef, Suspense } from "react";
import { P5Canvas } from "@p5-wrapper/react";
import type { DemoSlideProps, PlaylistResponse } from "./demo-types";
import { demoBeamSearchSketch } from "../sketches/demoBeamSearch";
import { T } from "../theme";
import precomputedPlaylist from "../data/playlist.json";

export function DemoGenerating({
  isActive,
  replayKey,
  demoState,
  setDemoState,
  onNext,
}: DemoSlideProps) {
  const { startTrack, endTrack, playlist, isLoading } = demoState;
  // Track whether we've already fired the request for this activation
  const firedRef = useRef(false);

  useEffect(() => {
    if (!isActive) {
      firedRef.current = false;
      return;
    }
    if (!startTrack || !endTrack) return;
    if (playlist || isLoading) return;
    if (firedRef.current) return;

    firedRef.current = true;
    setDemoState((s) => ({ ...s, isLoading: true, error: null }));

    const timer = setTimeout(() => {
      setDemoState((s) => ({
        ...s,
        playlist: precomputedPlaylist as unknown as PlaylistResponse,
        isLoading: false,
      }));
      onNext?.();
    }, 10_000);
    return () => clearTimeout(timer);
  }, [isActive]);

  return (
    <div className={`slide ${isActive ? "active" : ""}`}>
      <h2 className="slide-title">Generating Your Playlist</h2>
      <p className="slide-subtitle">
        Running beam search across music feature space…
      </p>

      {/* Full-slide canvas underlay */}
      <div style={{ position: "absolute", inset: 0, zIndex: -1 }}>
        <Suspense fallback={null}>
          <P5Canvas
            sketch={demoBeamSearchSketch}
            isActive={isActive && (isLoading || !playlist)}
            replayKey={replayKey}
            startTitle={startTrack?.title ?? ""}
            startArtist={startTrack?.artist ?? ""}
            endTitle={endTrack?.title ?? ""}
            endArtist={endTrack?.artist ?? ""}
          />
        </Suspense>
      </div>

      {/* Overlay: track pills, status, error — sit on top of the canvas */}
      <div
        style={{
          position: "absolute",
          left: T.MARGIN,
          right: T.MARGIN,
          bottom: 40,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 20,
          zIndex: 1,
        }}
      >
        {/* Track names */}
        {startTrack && endTrack && (
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 20,
              fontSize: 16,
            }}
          >
            <TrackPill
              title={startTrack.title}
              artist={startTrack.artist}
              label="Start"
            />
            <span style={{ color: T.MUTED, fontSize: 24 }}>→</span>
            <TrackPill
              title={endTrack.title}
              artist={endTrack.artist}
              label="End"
            />
          </div>
        )}

        {/* Status */}
        {isLoading && (
          <p style={{ color: T.MUTED, fontStyle: "italic", fontSize: 15 }}>
            Evaluating transitions using the music knowledge base…
          </p>
        )}
      </div>
    </div>
  );
}

function TrackPill({
  title,
  artist,
  label,
}: {
  title: string | null;
  artist: string | null;
  label: string;
}) {
  return (
    <div
      className="card"
      style={{ padding: "10px 20px", textAlign: "center", minWidth: 220 }}
    >
      <p
        style={{
          fontSize: 11,
          color: T.MUTED,
          fontStyle: "italic",
          marginBottom: 4,
        }}
      >
        {label}
      </p>
      <p style={{ fontSize: 15, fontWeight: "bold" }}>{title ?? "Unknown"}</p>
      <p style={{ fontSize: 13, color: T.MUTED }}>{artist ?? ""}</p>
    </div>
  );
}
