import type { SlideProps } from "./types";

const ITEMS = [
  {
    heading: "Essentia Integration",
    body: "Replace archived AcousticBrainz with live audio analysis for new releases.",
    orange: true,
  },
  {
    heading: "Weight Optimisation",
    body: "Calibrate dimension weights against the Million Playlist Dataset.",
    orange: false,
  },
  {
    heading: "Real-Time Analysis",
    body: "Stream audio features during playback for dynamic playlist adjustment.",
    orange: true,
  },
  {
    heading: "Multi-Modal Input",
    body: '"Take me from chill morning to party night" — natural language playlist goals.',
    orange: false,
  },
] as const;

export function Future({ isActive }: SlideProps) {
  const dotX = 100;
  const startY = 175;
  const itemH = 115;

  return (
    <div className={`slide ${isActive ? "active" : ""}`}>
      <h2 className="slide-title">What's Next</h2>

      {/* Vertical timeline line */}
      <div
        style={{
          position: "absolute",
          left: dotX - 1,
          top: startY + 8,
          width: 2,
          height: (ITEMS.length - 1) * itemH + 10,
          background: "#e0e0e0",
        }}
      />

      {/* Timeline items */}
      {ITEMS.map((item, i) => (
        <div
          key={i}
          className="animate-item"
          style={{
            position: "absolute",
            top: startY + i * itemH,
            left: 0,
            right: 60,
            display: "flex",
            alignItems: "flex-start",
            animationDelay: `${i * 0.2}s`,
          }}
        >
          {/* Dot */}
          <div
            style={{
              position: "absolute",
              left: dotX - 9,
              top: 12,
              width: 18,
              height: 18,
              borderRadius: "50%",
              background: item.orange ? "#e8590c" : "#1a1a1a",
              flexShrink: 0,
            }}
          />

          {/* Text */}
          <div style={{ marginLeft: 150, textAlign: "left" }}>
            <p
              style={{
                fontSize: 23,
                fontWeight: "bold",
                color: item.orange ? "#e8590c" : "#1a1a1a",
                marginBottom: 6,
              }}
            >
              {item.heading}
            </p>
            <p style={{ fontSize: 15, color: "#9ca3af", lineHeight: 1.5 }}>
              {item.body}
            </p>
          </div>
        </div>
      ))}
    </div>
  );
}
