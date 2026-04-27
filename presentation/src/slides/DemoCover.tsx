import type { SlideProps } from "./types";

export function DemoCover({ isActive }: SlideProps) {
  return (
    <div className={`slide ${isActive ? "active" : ""}`}>
      <div
        style={{
          position: "absolute",
          inset: 0,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          gap: 16,
        }}
      >
        <p style={{ fontSize: 16, letterSpacing: "0.2em", textTransform: "uppercase", color: "rgba(255,255,255,0.7)" }}>
          Live Demo
        </p>
        <h1
          style={{
            fontFamily: "var(--font-heading)",
            fontSize: 72,
            fontWeight: "bold",
            color: "#ffffff",
            lineHeight: 1,
          }}
        >
          Wave Guide
        </h1>
        <p style={{ fontSize: 22, color: "rgba(255,255,255,0.85)", fontStyle: "italic", fontFamily: "var(--font-heading)" }}>
          From one song to another
        </p>
      </div>
    </div>
  );
}
