import { useEffect, useRef, Suspense } from "react";
import { P5Canvas } from "@p5-wrapper/react";
import type { DemoSlideProps } from "./demo-types";
import { demoBeamSearchSketch } from "../sketches/demoBeamSearch";
import { T } from "../theme";

export function DemoGenerating({
  isActive,
  replayKey,
  demoState,
  setDemoState,
  onNext,
}: DemoSlideProps) {
  const { startTrack, endTrack, playlist, isLoading, error } = demoState;
  // Track whether we've already fired the request for this activation
  const firedRef = useRef(false);

  useEffect(() => {
    if (!isActive) {
      firedRef.current = false;
      return;
    }
    if (!startTrack || !endTrack) return;
    if (playlist || isLoading || error) return;
    if (firedRef.current) return;

    firedRef.current = true;
    setDemoState((s) => ({ ...s, isLoading: true, error: null }));

    const params = new URLSearchParams({
      source_mbid: startTrack.mbid,
      dest_mbid: endTrack.mbid,
      length: "7",
      beam_width: "10",
    });

    fetch(`/api/playlist?${params}`)
      .then((r) => {
        if (r.ok) return r.json();
        return r
          .json()
          .then((e: { error?: string }) =>
            Promise.reject(e.error ?? `HTTP ${r.status}`),
          );
      })
      .then((data) => {
        setDemoState((s) => ({ ...s, playlist: data, isLoading: false }));
        onNext?.();
      })
      .catch((err: unknown) => {
        setDemoState((s) => ({ ...s, error: String(err), isLoading: false }));
      });
  }, [isActive]);

  function retry() {
    firedRef.current = false;
    setDemoState((s) => ({
      ...s,
      isLoading: false,
      error: null,
      playlist: null,
    }));
  }

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
            isActive={isActive && (isLoading || (!playlist && !error))}
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

        {/* Error state */}
        {error && (
          <div
            className="card"
            style={{
              border: `1.5px solid #ef4444`,
              padding: "20px 28px",
              maxWidth: 560,
              textAlign: "center",
            }}
          >
            <p
              style={{ fontWeight: "bold", color: "#ef4444", marginBottom: 8 }}
            >
              Generation failed
            </p>
            <p style={{ color: T.MUTED, fontSize: 14, marginBottom: 16 }}>
              {error}
            </p>
            <button
              className="btn"
              onClick={retry}
              style={{ padding: "8px 24px" }}
            >
              Try Again
            </button>
          </div>
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
