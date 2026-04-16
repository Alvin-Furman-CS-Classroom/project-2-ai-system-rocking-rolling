import { Code } from "@revealjs/react";
import type { SlideProps } from "./types";

export function ProbLog({ isActive }: SlideProps) {
  return (
    <div className={`slide ${isActive ? "active" : ""}`}>
      <h2 className="slide-title">Music Theory Compatibility Rules</h2>
      <p className="slide-subtitle">Probabilistic Logic with ProbLog</p>

      {/* Left column: info cards */}
      <div style={{ position: "absolute", top: 152, left: 60, width: 510 }}>
        {/* What is ProbLog */}
        <div className="card card--orange" style={{ marginBottom: 14 }}>
          <h3 style={{ color: "#e8590c", fontSize: 18, marginBottom: 10 }}>
            What is ProbLog?
          </h3>
          <ul
            style={{
              fontSize: 15,
              lineHeight: 1.7,
              paddingLeft: 18,
              color: "#1a1a1a",
              textAlign: "left",
            }}
          >
            <li>Logic programming extended with probabilities</li>
            <li>
              Facts carry a confidence score —{" "}
              <code
                style={{
                  background: "#fde8d8",
                  padding: "1px 5px",
                  borderRadius: 3,
                  fontSize: 13,
                  fontFamily: "monospace",
                }}
              >
                0.82::key_compatible(t1, t2)
              </code>
            </li>
            <li>Queries return a probability, not just true/false</li>
          </ul>
        </div>

        {/* How Wave Guide uses it */}
        <div className="card">
          <h3 style={{ fontSize: 18, marginBottom: 10 }}>
            How Wave Guide Uses It
          </h3>
          <ul
            style={{
              fontSize: 15,
              lineHeight: 1.7,
              paddingLeft: 18,
              color: "#1a1a1a",
              textAlign: "left",
            }}
          >
            <li>
              <strong>11 compatibility dimensions</strong> — key, tempo, energy,
              loudness, mood, timbre, tags, popularity, artist, era, genre
            </li>
            <li>
              Python computes continuous probabilities from audio features and
              asserts them as ProbLog facts
            </li>
            <li>
              Mood uses <strong style={{ color: "#e8590c" }}>noisy-OR</strong> ·
              genre uses{" "}
              <strong style={{ color: "#e8590c" }}>dot product</strong> · era
              uses <strong style={{ color: "#e8590c" }}>Gaussian decay</strong>
            </li>
          </ul>
        </div>
      </div>

      {/* Right column: code */}
      <div style={{ position: "absolute", top: 132, left: 598, right: 40 }}>
        <p
          style={{
            fontSize: 12,
            color: "#9ca3af",
            fontStyle: "italic",
            marginBottom: 8,
            textAlign: "right",
          }}
        >
          music_theory.pl
        </p>
        <Code
          lang="pl"
          style={{
            fontSize: "1.1rem",
            lineHeight: "1.55",
            textAlign: "left",
            width: "100%",
          }}
        >
          {`smooth_transition(T1, T2) :-
    key_compatible(T1, T2),
    tempo_compatible(T1, T2),
    energy_compatible(T1, T2),
    loudness_compatible(T1, T2),
    mood_compatible(T1, T2),
    timbre_compatible(T1, T2),
    tag_compatible(T1, T2),
    popularity_compatible(T1, T2),
    artist_compatible(T1, T2),
    era_compatible(T1, T2),
    mb_genre_compatible(T1, T2).`}
        </Code>
      </div>
    </div>
  );
}
