import { useCallback, useEffect, useRef, useState } from "react";
import { Deck, Slide } from "@revealjs/react";
import type { RevealApi } from "reveal.js";
import "reveal.js/reveal.css";
import "reveal.js/plugin/highlight/monokai.css";
import RevealHighlight from "reveal.js/plugin/highlight";
import "./presentation.css";

import { Title } from "./slides/Title";
import { Problem } from "./slides/Problem";
import { Architecture } from "./slides/Architecture";
import { Radar } from "./slides/Radar";
import { Compatibility } from "./slides/Compatibility";
import { BeamSearch } from "./slides/BeamSearch";
import { Constraints } from "./slides/Constraints";
import { Preferences } from "./slides/Preferences";
import { Mood } from "./slides/Mood";
import { Infrastructure } from "./slides/Infrastructure";
import { DemoCover } from "./slides/DemoCover";
import { Future } from "./slides/Future";
import { ThankYou } from "./slides/ThankYou";
import { ProbLog } from "./slides/ProbLog";

import { DemoGenres } from "./slides/DemoGenres";
import { DemoArtists } from "./slides/DemoArtists";
import { DemoPreferences } from "./slides/DemoPreferences";
import { DemoMoodJourney } from "./slides/DemoMoodJourney";
import { DemoSuggestions } from "./slides/DemoSuggestions";
import { DemoGenerating } from "./slides/DemoGenerating";
import { DemoPlaylist } from "./slides/DemoPlaylist";

import type { SlideProps } from "./slides/types";
import type { DemoSlideProps, DemoState } from "./slides/demo-types";
import { INITIAL_DEMO_STATE } from "./slides/demo-types";

// Slides before the demo section
const PRE_DEMO_SLIDES = [
  Title,
  Problem,
  Architecture,
  Infrastructure,
  Radar,
  ProbLog,
  Compatibility,
  BeamSearch,
  Constraints,
  Preferences,
  Mood,
] as React.ComponentType<SlideProps>[];

// Demo slides (receive DemoSlideProps)
const DEMO_SLIDES = [
  DemoGenres,
  DemoArtists,
  DemoPreferences,
  DemoMoodJourney,
  DemoSuggestions,
  DemoGenerating,
  DemoPlaylist,
] as React.ComponentType<DemoSlideProps>[];

// Slides after the demo section
const POST_DEMO_SLIDES = [
  Future,
  ThankYou,
] as React.ComponentType<SlideProps>[];

const DEMO_COVER_INDEX = PRE_DEMO_SLIDES.length;
const DEMO_START = DEMO_COVER_INDEX + 1;
const DEMO_END = DEMO_START + DEMO_SLIDES.length - 1;
const TOTAL_SLIDES = PRE_DEMO_SLIDES.length + 1 + DEMO_SLIDES.length + POST_DEMO_SLIDES.length;

export function Presentation() {
  const [activeIndex, setActiveIndex] = useState(0);
  const [replayKey, setReplayKey] = useState(0);
  const [demoState, setDemoState] = useState<DemoState>(INITIAL_DEMO_STATE);
  const deckApiRef = useRef<RevealApi | null>(null);

  const handleDeckRef = useCallback((ref: RevealApi | null) => {
    deckApiRef.current = ref;
  }, []);

  const goNext = useCallback(() => {
    deckApiRef.current?.next();
  }, []);

  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "r" || e.key === "R") {
        setReplayKey((k) => k + 1);
      }
    };
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, []);

  return (
    <Deck
      plugins={[RevealHighlight]}
      style={{ width: "100%", height: "100%" }}
      deckRef={handleDeckRef}
      onReady={(deck) => {
        setActiveIndex(deck.getIndices().h);
      }}
      onSlideChange={(event) => {
        const e = event as Event & { indexh?: number };
        setActiveIndex(e.indexh ?? 0);
      }}
      config={{
        controls: true,
        progress: true,
        hash: true,
        transition: "none",
        width: 1280,
        height: 720,
        margin: 0,
        minScale: 0.1,
        maxScale: 3,
        keyboard: {
          82: () => setReplayKey((k) => k + 1),
        },
      }}
    >
      {/* Pre-demo slides */}
      {PRE_DEMO_SLIDES.map((SlideComponent, i) => (
        <Slide key={`pre-${i}`}>
          <SlideComponent
            isActive={activeIndex === i}
            replayKey={activeIndex === i ? replayKey : 0}
          />
        </Slide>
      ))}

      {/* Demo cover */}
      <Slide backgroundColor="#e8590c">
        <DemoCover isActive={activeIndex === DEMO_COVER_INDEX} replayKey={0} />
      </Slide>

      {/* Demo slides */}
      {DEMO_SLIDES.map((SlideComponent, i) => {
        const globalIndex = DEMO_START + i;
        return (
          <Slide key={`demo-${i}`}>
            <SlideComponent
              isActive={activeIndex === globalIndex}
              replayKey={activeIndex === globalIndex ? replayKey : 0}
              demoState={demoState}
              setDemoState={setDemoState}
              onNext={goNext}
            />
          </Slide>
        );
      })}

      {/* Post-demo slides */}
      {POST_DEMO_SLIDES.map((SlideComponent, i) => {
        const globalIndex = DEMO_END + 1 + i;
        return (
          <Slide key={`post-${i}`}>
            <SlideComponent
              isActive={activeIndex === globalIndex}
              replayKey={activeIndex === globalIndex ? replayKey : 0}
            />
          </Slide>
        );
      })}
    </Deck>
  );
}

// Expose for debugging
export { DEMO_START, DEMO_END, TOTAL_SLIDES };
