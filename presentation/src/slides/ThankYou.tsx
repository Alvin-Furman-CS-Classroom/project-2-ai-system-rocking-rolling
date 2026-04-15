import { Suspense } from "react";
import { createPortal } from "react-dom";
import { P5Canvas } from "@p5-wrapper/react";
import type { SlideProps } from "./types";
import { waveformSketch } from "../sketches/waveform";

export function ThankYou({ isActive, replayKey }: SlideProps) {
  return (
    <div className={`slide ${isActive ? "active" : ""}`}>
      {/* Centered text */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          paddingBottom: 100,
        }}
      >
        <h1
          className="animate-item"
          style={{
            fontSize: 96,
            fontWeight: "bold",
            color: "#1a1a1a",
            margin: 0,
            lineHeight: 1.1,
            textAlign: "center",
            animationDelay: "0s",
          }}
        >
          Thank You
        </h1>
        <p
          className="animate-item"
          style={{
            fontSize: 21,
            color: "#1a1a1a",
            margin: "24px 0 0",
            textAlign: "center",
            animationDelay: "0.4s",
          }}
        >
          Michael Thomas &nbsp;&nbsp;·&nbsp;&nbsp; Rahul Ranjan Sah
        </p>
        <p
          className="animate-item"
          style={{
            fontSize: 48,
            fontWeight: "bold",
            color: "#e8590c",
            margin: "32px 0 0",
            textAlign: "center",
            animationDelay: "1s",
          }}
        >
          Questions?
        </p>
      </div>

      {/* Waveform — portalled to body so it escapes Reveal.js scaling */}
      {isActive &&
        createPortal(
          <div className="waveform-portal">
            <Suspense fallback={null}>
              <P5Canvas
                sketch={waveformSketch}
                isActive={isActive}
                replayKey={replayKey}
              />
            </Suspense>
          </div>,
          document.body,
        )}
    </div>
  );
}
