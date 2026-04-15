import type { P5CanvasInstance, Sketch, SketchProps } from '@p5-wrapper/react';
import type { ThemeHelpers } from '../p5helpers';
import { createThemeHelpers, ctx2d } from '../p5helpers';
import { T } from '../theme';

const DIMS = [
  ['Key',      0.75, 0.60],
  ['Tempo',    0.68, 0.45],
  ['Energy',   0.75, 0.60],
  ['Loudness', 0.82, 0.70],
  ['Mood',     0.90, 0.35],
  ['Timbre',   0.55, 0.65],
  ['Genre',    0.70, 0.30],
  ['Tags',     0.65, 0.40],
] as const;

const FINAL_SCORE = 62;

type Props = SketchProps & { isActive: boolean; replayKey: number };

export const compatibilitySketch: Sketch<Props> = (p: P5CanvasInstance<Props>) => {
  let h: ThemeHelpers;
  let localFrame = 0;
  let wasActive = false;
  let lastReplayKey = 0;

  function enter() { localFrame = 0; }

  p.setup = () => {
    p.createCanvas(1160, 440);
    p.textFont('Noto Serif');
    h = createThemeHelpers(p);
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
    localFrame++;

    const startY = 20;
    const rowH = 36;
    const barAreaW = 260;
    const cx = 580; // center of 1160px canvas

    DIMS.forEach(([dim, va, vb], i) => {
      const fade = p.constrain((localFrame - i * 8) / 18, 0, 1);
      const y = startY + i * rowH;

      p.push();
      ctx2d(p).globalAlpha = fade;

      h.drawText(dim, cx, y + 8, { size: 14, color: T.MUTED, align: 'center' });

      // Left bar (orange, extends from center leftward)
      const aFrac = h.easeOut(fade) * va;
      p.noStroke();
      p.fill(T.ORANGE);
      p.rect(cx - 60 - barAreaW * aFrac, y + 5, barAreaW * aFrac, 16, 3);
      p.noFill();
      p.stroke(T.BORDER);
      p.strokeWeight(0.8);
      p.rect(cx - 60 - barAreaW, y + 5, barAreaW, 16, 3);

      // Right bar (dark, extends from center rightward)
      const bFrac = h.easeOut(fade) * vb;
      p.noStroke();
      p.fill(T.TEXT);
      p.rect(cx + 60, y + 5, barAreaW * bFrac, 16, 3);
      p.noFill();
      p.stroke(T.BORDER);
      p.strokeWeight(0.8);
      p.rect(cx + 60, y + 5, barAreaW, 16, 3);

      h.drawText(`${Math.round(va * 100)}%`, cx - 70 - barAreaW, y + 8,
        { size: 12, bold: true, color: T.ORANGE, align: 'right' });
      h.drawText(`${Math.round(vb * 100)}%`, cx + 70 + barAreaW, y + 8,
        { size: 12, bold: true, color: T.TEXT });

      p.pop();
    });

    // Final score
    const totalDur = DIMS.length * 8 + 18;
    const scoreFade = p.constrain((localFrame - totalDur - 10) / 30, 0, 1);
    const animScore = Math.round(h.easeOut(scoreFade) * FINAL_SCORE);

    p.push();
    ctx2d(p).globalAlpha = scoreFade;
    h.drawCard(cx - 180, 360, 360, 70, { fill: T.ORANGE_L, stroke: T.ORANGE });
    h.drawText('Compatibility:', cx - 10, 395, { size: 18, color: T.MUTED, align: 'right', vAlign: 'center' });
    h.drawText(`${animScore}%`, cx + 100, 395, { size: 36, bold: true, color: T.ORANGE, align: 'center', vAlign: 'center' });
    p.pop();

    if (localFrame > totalDur + 60) p.noLoop();
  };
};
