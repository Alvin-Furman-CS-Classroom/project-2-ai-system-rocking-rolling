import type { P5CanvasInstance, Sketch, SketchProps } from '@p5-wrapper/react';
import { ctx2d } from '../p5helpers';
import { T } from '../theme';

const ENERGY_VALS = [0.3, 0.45, 0.55, 0.75, 0.9];
const W = 340, H = 160;

type Props = SketchProps & { isActive: boolean; replayKey: number };

export const energyArcSketch: Sketch<Props> = (p: P5CanvasInstance<Props>) => {
  let arcFrame = 0;
  let wasActive = false;
  let lastReplayKey = 0;

  function enter() { arcFrame = 0; }

  p.setup = () => {
    p.createCanvas(W, H);
    p.textFont('Noto Serif');
    enter();
  };

  p.updateWithProps = (props: Props) => {
    const replay = props.isActive && props.replayKey !== lastReplayKey;
    if ((props.isActive && !wasActive) || replay) { enter(); p.loop(); }
    else if (!props.isActive && wasActive) { p.noLoop(); }
    wasActive = props.isActive;
    lastReplayKey = props.replayKey;
  };

  p.draw = () => {
    p.background(T.BG);
    arcFrame++;
    if (arcFrame > 200) arcFrame = 0;

    const dur = 100;
    const progress = Math.min(arcFrame / dur, 1);
    const padL = 35, padB = 25, padT = 10;

    // Axes
    p.stroke(T.BORDER); p.strokeWeight(1);
    p.line(padL, H - padB, W, H - padB);
    p.line(padL, padT, padL, H - padB);

    // Axis labels
    p.noStroke(); p.fill(T.MUTED);
    p.textFont('Noto Serif'); p.textSize(11);
    p.textAlign(p.CENTER, p.TOP);
    p.text('Track Position', padL + (W - padL) / 2, H - padB + 8);

    p.push();
    p.translate(12, padT + (H - padT - padB) / 2);
    p.rotate(-Math.PI / 2);
    p.text('Energy', 0, 0);
    p.pop();

    // Dashed guide line
    p.stroke(T.BORDER); p.strokeWeight(1);
    ctx2d(p).setLineDash([4, 4]);
    p.line(padL, H - padB - 0.25 * (H - padT - padB), W, H - padB - 0.9 * (H - padT - padB));
    ctx2d(p).setLineDash([]);

    // Animated polyline
    const n = ENERGY_VALS.length;
    const points = ENERGY_VALS.map((v, i) => {
      const px = padL + (i / (n - 1)) * (W - padL);
      const targetY = (H - padB) - v * (H - padT - padB);
      const startY = H - padB;
      const easeOut = (t: number) => 1 - Math.pow(1 - t, 3);
      const localT = p.constrain(progress * n - i + 0.5, 0, 1);
      return { x: px, y: startY + (targetY - startY) * easeOut(localT) };
    });

    p.stroke(T.ORANGE); p.strokeWeight(2.5); p.noFill();
    p.beginShape();
    for (const pt of points) p.vertex(pt.x, pt.y);
    p.endShape();

    p.noStroke(); p.fill(T.ORANGE);
    for (let i = 0; i < n; i++) {
      const localT = p.constrain(progress * n - i + 0.5, 0, 1);
      if (localT > 0) p.circle(points[i].x, points[i].y, 8);
    }

    if (progress > 0.95) {
      ctx2d(p).globalAlpha = p.constrain((progress - 0.95) / 0.05, 0, 1);
      p.fill(T.ORANGE);
      p.textSize(14); p.textStyle(p.BOLD);
      p.textAlign(p.RIGHT, p.TOP);
      p.text('Rising ↗', W - 8, padT + 2);
      ctx2d(p).globalAlpha = 1;
    }
  };
};
