import type { DemoSlideProps } from "./demo-types";
import { T } from "../theme";
import genreArtistsData from "../data/genre_artists.json";

const genreArtists = genreArtistsData as Record<
  string,
  Record<string, string[]>
>;

export function DemoArtists({
  isActive,
  demoState,
  setDemoState,
  onNext,
}: DemoSlideProps) {
  const { selectedGenres, selectedArtists } = demoState;

  // Collect unique artists across selected genres
  const artists = [
    ...new Set(
      selectedGenres.flatMap((g) => Object.keys(genreArtists[g] ?? {})),
    ),
  ].sort();

  function toggle(artist: string) {
    const isSelected = selectedArtists.includes(artist);
    setDemoState((s) => ({
      ...s,
      selectedArtists: isSelected
        ? s.selectedArtists.filter((a) => a !== artist)
        : [...s.selectedArtists, artist],
      startTrack: null,
      endTrack: null,
      playlist: null,
    }));
  }

  const canAdvance = selectedArtists.length > 0;

  return (
    <div className={`slide ${isActive ? "active" : ""}`}>
      <h2 className="slide-title">Pick Your Artists</h2>
      <p className="slide-subtitle">
        {artists.length > 0
          ? `${artists.length} artists across your selected genres`
          : "Go back and select some genres first"}
      </p>

      {/* Artist grid */}
      <div
        style={{
          position: "absolute",
          top: 155,
          left: T.MARGIN,
          right: T.MARGIN,
          bottom: 80,
          display: "flex",
          flexWrap: "wrap",
          gap: 12,
          alignContent: "flex-start",
          overflowY: "auto",
          paddingBottom: 8,
        }}
      >
        {artists.length === 0 ? (
          <p style={{ color: T.MUTED, fontStyle: "italic", fontSize: 16 }}>
            No artists found — select genres on the previous slide.
          </p>
        ) : (
          artists.map((artist, i) => {
            const isSelected = selectedArtists.includes(artist);
            return (
              <div
                key={artist}
                onClick={() => toggle(artist)}
                className="animate-item"
                style={{
                  padding: "10px 20px",
                  cursor: "pointer",
                  borderRadius: 6,
                  border: `2px solid ${isSelected ? T.ORANGE : T.BORDER}`,
                  background: isSelected ? T.ORANGE_L : T.SURFACE,
                  fontSize: 15,
                  fontWeight: "bold",
                  color: isSelected ? T.ORANGE : T.TEXT,
                  transition: "border-color 0.15s, background 0.15s",
                  userSelect: "none",
                  animationDelay: `${i * 0.04}s`,
                  whiteSpace: "nowrap",
                }}
              >
                {artist}
              </div>
            );
          })
        )}
      </div>

      {/* Selected count */}
      {selectedArtists.length > 0 && (
        <p
          style={{
            position: "absolute",
            bottom: 34,
            left: T.MARGIN,
            fontSize: 14,
            color: T.MUTED,
            fontStyle: "italic",
          }}
        >
          {selectedArtists.length} artist
          {selectedArtists.length !== 1 ? "s" : ""} selected
        </p>
      )}

      {/* Continue button */}
      <button
        className="btn"
        onClick={() => canAdvance && onNext?.()}
        style={{
          position: "absolute",
          bottom: 28,
          right: T.MARGIN,
          padding: "10px 28px",
          fontSize: 15,
          fontWeight: "bold",
          background: canAdvance ? T.ORANGE : undefined,
          color: canAdvance ? "#fff" : undefined,
          borderColor: canAdvance ? T.ORANGE : undefined,
          opacity: canAdvance ? 1 : 0.35,
          cursor: canAdvance ? "pointer" : "not-allowed",
        }}
      >
        Continue →
      </button>
    </div>
  );
}
