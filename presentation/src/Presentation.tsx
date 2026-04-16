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
import { WebUI } from "./slides/WebUI";
import { Future } from "./slides/Future";
import { ThankYou } from "./slides/ThankYou";
import { ProbLog } from "./slides/ProbLog";

const SLIDES = [
  Title,
  Problem,
  Architecture,
  Radar,
  ProbLog,
  Compatibility,
  BeamSearch,
  Constraints,
  Preferences,
  Mood,
  Infrastructure,
  WebUI,
  Future,
  ThankYou,
];

export function Presentation() {
  const [activeIndex, setActiveIndex] = useState(0);
  const [replayKey, setReplayKey] = useState(0);
  const deckApiRef = useRef<RevealApi | null>(null);

  const handleDeckRef = useCallback((ref: RevealApi | null) => {
    deckApiRef.current = ref;
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
      {SLIDES.map((SlideComponent, i) => (
        <Slide key={i}>
          <SlideComponent
            isActive={activeIndex === i}
            replayKey={activeIndex === i ? replayKey : 0}
          />
        </Slide>
      ))}
    </Deck>
  );
}
