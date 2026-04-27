import { Suspense, useEffect, useState } from "react";
import { P5Canvas } from "@p5-wrapper/react";
import type { SlideProps } from "./types";
import { radarSketch, SONGS, DIMS } from "../sketches/radar";

const ALBUM_ART: (string | null)[] = [
  "/gjwhf.jpg", // Girls Just Wanna Have Fun
  "/cn.png", // Comfortably Numb
  "/mozno35.jpg", // Symphony No. 35
  "/br.jpg", // Bohemian Rhapsody
];

export function Radar({ isActive, replayKey }: SlideProps) {
  const [selectedSong, setSelectedSong] = useState(0);
  const song = SONGS[selectedSong];

  // Auto-cycle through songs every 5s while the slide is active
  useEffect(() => {
    if (!isActive) return;
    const id = setInterval(() => {
      setSelectedSong((s) => (s + 1) % SONGS.length);
    }, 5000);
    return () => clearInterval(id);
  }, [isActive]);

  return (
    <div className={`slide ${isActive ? "active" : ""}`}>
      <h2 className="slide-title">A Musical Fingerprint</h2>
      <p className="slide-subtitle">11-dimensional feature vector per track</p>

      {/* Left panel: radar chart */}
      <div style={{ position: "absolute", top: 150, left: 60 }}>
        <Suspense fallback={null}>
          <P5Canvas
            sketch={radarSketch}
            isActive={isActive}
            replayKey={replayKey}
            selectedSong={selectedSong}
          />
        </Suspense>
      </div>

      {/* Right panel: song selector + info */}
      <div
        style={{
          position: "absolute",
          top: 150,
          left: 640,
          right: 60,
          bottom: 60,
        }}
      >
        {/* Song buttons */}
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {SONGS.map((s, i) => (
            <button
              key={i}
              className={`btn ${selectedSong === i ? "active" : ""}`}
              onClick={() => setSelectedSong(i)}
              style={{
                textAlign: "left",
                padding: "10px 16px",
                display: "flex",
                alignItems: "center",
                gap: 12,
                ...(selectedSong === i && {
                  background: `${SONGS[i].color}18`,
                  borderColor: SONGS[i].color,
                  color: SONGS[i].color,
                }),
              }}
            >
              {ALBUM_ART[i] ? (
                <img
                  src={ALBUM_ART[i]!}
                  alt={s.name}
                  style={{
                    width: 40,
                    height: 40,
                    borderRadius: 6,
                    objectFit: "cover",
                    flexShrink: 0,
                  }}
                />
              ) : (
                <div
                  style={{
                    width: 40,
                    height: 40,
                    borderRadius: 6,
                    background: "#e0e0e0",
                    flexShrink: 0,
                  }}
                />
              )}
              <span>
                <span style={{ fontWeight: "bold", display: "block" }}>
                  {s.name}
                </span>
                <span style={{ color: "#9ca3af", fontSize: 13 }}>
                  {s.artist}
                </span>
              </span>
            </button>
          ))}
        </div>

        {/* Song info card — colored by song */}
        <div
          className="card"
          style={{
            marginTop: 24,
            borderColor: song.color,
            background: `${song.color}12`,
          }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "center",
              textAlign: "left",
              gap: 14,
              marginBottom: 12,
            }}
          >
            {ALBUM_ART[selectedSong] ? (
              <img
                src={ALBUM_ART[selectedSong]!}
                alt={song.name}
                style={{
                  width: 56,
                  height: 56,
                  borderRadius: 8,
                  objectFit: "cover",
                  flexShrink: 0,
                }}
              />
            ) : (
              <div
                style={{
                  width: 56,
                  height: 56,
                  borderRadius: 8,
                  background: "#e0e0e0",
                  flexShrink: 0,
                }}
              />
            )}
            <div>
              <h3 style={{ color: song.color, marginBottom: 4 }}>
                {song.name}
              </h3>
              <p
                style={{
                  color: "#9ca3af",
                  fontSize: 14,
                  fontStyle: "italic",
                  margin: 0,
                }}
              >
                {song.artist}
              </p>
            </div>
          </div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: "6px 12px" }}>
            {DIMS.map((dim, i) => (
              <span
                key={dim}
                style={{
                  fontSize: 12,
                  color: "#1a1a1a",
                }}
              >
                {dim}: <strong>{Math.round(song.vals[i] * 100)}%</strong>
              </span>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
