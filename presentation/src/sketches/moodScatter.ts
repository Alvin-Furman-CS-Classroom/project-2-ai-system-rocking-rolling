import type { P5CanvasInstance, Sketch, SketchProps } from "@p5-wrapper/react";
import type { ThemeHelpers } from "../p5helpers";
import { createThemeHelpers, ctx2d } from "../p5helpers";
import { T } from "../theme";

const W = 1160,
  H = 420;

const MOODS = [
  { name: "Calm", cx: 220, cy: 250, color: T.MUTED },
  { name: "Chill", cx: 370, cy: 150, color: T.MUTED },
  { name: "Sad", cx: 260, cy: 120, color: T.TEXT },
  { name: "Happy", cx: 730, cy: 130, color: T.ORANGE },
  { name: "Energized", cx: 920, cy: 260, color: T.ORANGE },
  { name: "Intense", cx: 810, cy: 330, color: T.TEXT },
] as const;

type Dot = { x: number; y: number; color: string; cluster: number };

type Props = SketchProps & {
  isActive: boolean;
  replayKey: number;
  selectedMood: number;
};

export const moodScatterSketch: Sketch<Props> = (
  p: P5CanvasInstance<Props>,
) => {
  let h: ThemeHelpers;
  let localFrame = 0;
  let selectedMood = 3;
  let wasActive = false;
  let lastReplayKey = 0;
  let dots: Dot[] = [];

  function generateDots() {
    let s = 42;
    const rand = () => {
      s = (s * 16807) % 2147483647;
      return (s - 1) / 2147483646;
    };
    dots = [];
    MOODS.forEach((m, mi) => {
      for (let i = 0; i < 28; i++) {
        dots.push({
          x: m.cx + (rand() - 0.5) * 130,
          y: m.cy + (rand() - 0.5) * 90,
          color: m.color,
          cluster: mi,
        });
      }
    });
  }

  function enter() {
    localFrame = 0;
    generateDots();
  }

  p.setup = () => {
    p.createCanvas(W, H);
    p.textFont("Noto Serif");
    h = createThemeHelpers(p);
    enter();
  };

  p.updateWithProps = (props: Props) => {
    selectedMood = props.selectedMood ?? 3;
    const replay = props.isActive && props.replayKey !== lastReplayKey;
    if ((props.isActive && !wasActive) || replay) {
      enter();
      p.loop();
    } else if (!props.isActive && wasActive) {
      p.noLoop();
    }
    wasActive = props.isActive;
    lastReplayKey = props.replayKey;
  };

  p.draw = () => {
    p.background(T.BG);
    localFrame++;

    h.drawCard(0, 0, W, H, { fill: T.SURFACE });

    // Cluster dots (staggered fade-in per cluster)
    dots.forEach((d) => {
      const start = d.cluster * 12;
      const t = p.constrain((localFrame - start) / 25, 0, 1);
      if (t <= 0) return;
      p.noStroke();
      ctx2d(p).globalAlpha = 0.35 * t;
      p.fill(d.color);
      p.circle(d.x, d.y, 7);
      ctx2d(p).globalAlpha = 1;
    });

    // Boundary circles (dashed)
    MOODS.forEach((m, i) => {
      const start = i * 12 + 15;
      const t = p.constrain((localFrame - start) / 20, 0, 1);
      if (t <= 0) return;
      p.noFill();
      p.stroke(m.color);
      p.strokeWeight(1.2);
      ctx2d(p).setLineDash([5, 5]);
      ctx2d(p).globalAlpha = 0.3 * t;
      p.circle(m.cx, m.cy, 130);
      ctx2d(p).setLineDash([]);
      ctx2d(p).globalAlpha = 1;
    });

    // Mood labels
    MOODS.forEach((m, i) => {
      const start = i * 12 + 5;
      const t = p.constrain((localFrame - start) / 20, 0, 1);
      ctx2d(p).globalAlpha = t;
      h.drawText(m.name, m.cx, m.cy - 75, {
        size: 16,
        bold: true,
        color: m.color,
        align: "center",
      });
      ctx2d(p).globalAlpha = 1;
    });

    // Selected centroid highlight (pulsing)
    if (localFrame > 40) {
      const m = MOODS[selectedMood];
      const pulse = 1 + 0.15 * Math.sin(localFrame * 0.1);
      p.noStroke();
      p.fill(232, 89, 12, 80);
      p.circle(m.cx, m.cy, 28 * pulse);
      p.stroke(T.ORANGE);
      p.strokeWeight(3);
      p.noFill();
      p.circle(m.cx, m.cy, 36 * pulse);
      p.noStroke();
      p.fill(T.ORANGE);
      p.circle(m.cx, m.cy, 14);
    }
  };
};
