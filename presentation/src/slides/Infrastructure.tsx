import { useState, useEffect } from "react";
import type { SlideProps } from "./types";
import mbLogo from "../assets/musicbrainz-logo.svg";
import abLogo from "../assets/acousticbrainz-logo.svg";
import lbLogo from "../assets/listenbrainz-logo.svg";

const SOURCES = [
  {
    name: "MusicBrainz",
    stats: ["38M recordings", "2.8M artists", "6.8M genre tags"],
    badge: "Postgres Mirror",
    color: "#ba478f",
    logo: mbLogo,
  },
  {
    name: "AcousticBrainz",
    stats: ["~7M recordings", "60+ descriptors", "MFCCs / spectral"],
    badge: "Archived API",
    color: "#4e7ec2",
    logo: abLogo,
  },
  {
    name: "ListenBrainz",
    stats: ["Live similarity graph", "4 algorithms merged", "User tags & listens"],
    badge: "Live API",
    color: "#353070",
    logo: lbLogo,
  },
] as const;

const INTERVAL_MS = 2800;

export function Infrastructure({ isActive, replayKey }: SlideProps) {
  const [activeIdx, setActiveIdx] = useState(0);

  useEffect(() => {
    if (!isActive) return;
    setActiveIdx(0);
    const id = setInterval(() => setActiveIdx((i) => (i + 1) % SOURCES.length), INTERVAL_MS);
    return () => clearInterval(id);
  }, [isActive, replayKey]);

  const src = SOURCES[activeIdx];

  return (
    <div className={`slide ${isActive ? "active" : ""}`}>
      <h2 className="slide-title">38 Million Recordings</h2>
      <p className="slide-subtitle">Open-Source Database Infrastructure</p>

      {/* Active service logo */}
      <div
        style={{
          position: "absolute",
          top: 185,
          left: 0,
          right: 0,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 10,
        }}
      >
        <img
          key={`logo-${activeIdx}`}
          src={src.logo}
          alt={src.name}
          style={{
            height: 80,
            maxWidth: 400,
            objectFit: "contain",
            animation: "fadeSlideIn 0.35s ease-out",
          }}
        />
      </div>

      {/* Source cards */}
      <div
        style={{
          position: "absolute",
          top: 340,
          left: 60,
          right: 60,
          display: "flex",
          gap: 30,
        }}
      >
        {SOURCES.map((s, i) => {
          const highlighted = i === activeIdx;
          return (
            <div
              key={i}
              className="card"
              style={{
                flex: 1,
                border: `${highlighted ? 2 : 1.5}px solid ${highlighted ? s.color : "#e0e0e0"}`,
                background: highlighted ? `${s.color}12` : "#f5f5f5",
                transition: "border-color 0.4s, background 0.4s, box-shadow 0.4s",
                boxShadow: highlighted ? `0 2px 18px ${s.color}30` : "none",
              }}
            >
              <h3
                style={{
                  color: highlighted ? s.color : "#1a1a1a",
                  marginBottom: 12,
                  transition: "color 0.4s",
                }}
              >
                {s.name}
              </h3>
              {s.stats.map((stat: string) => (
                <p key={stat} style={{ fontSize: 15, marginBottom: 6 }}>
                  • {stat}
                </p>
              ))}
              <div
                style={{
                  marginTop: 16,
                  display: "inline-block",
                  background: highlighted ? `${s.color}20` : "rgba(156,163,175,0.15)",
                  borderRadius: 4,
                  padding: "4px 12px",
                  fontSize: 12,
                  fontWeight: "bold",
                  color: highlighted ? s.color : "#9ca3af",
                  transition: "all 0.4s",
                }}
              >
                {s.badge}
              </div>
            </div>
          );
        })}
      </div>

      {/* Step dots */}
      <div
        style={{
          position: "absolute",
          bottom: 28,
          left: 0,
          right: 0,
          display: "flex",
          justifyContent: "center",
          gap: 10,
        }}
      >
        {SOURCES.map((s, i) => (
          <div
            key={i}
            style={{
              width: 8,
              height: 8,
              borderRadius: "50%",
              background: i === activeIdx ? s.color : "#d0d0d0",
              transition: "background 0.4s",
            }}
          />
        ))}
      </div>
    </div>
  );
}
