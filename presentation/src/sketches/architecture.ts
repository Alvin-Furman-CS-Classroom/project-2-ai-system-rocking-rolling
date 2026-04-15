import type { P5CanvasInstance, Sketch, SketchProps } from '@p5-wrapper/react';
import type { ThemeHelpers } from '../p5helpers';
import { createThemeHelpers, ctx2d } from '../p5helpers';
import { T } from '../theme';

type Props = SketchProps & { isActive: boolean; replayKey: number };

export const architectureSketch: Sketch<Props> = (p: P5CanvasInstance<Props>) => {
  let h: ThemeHelpers;
  let localFrame = 0;
  let wasActive = false;
  let lastReplayKey = 0;

  function enter() { localFrame = 0; }

  p.setup = () => {
    p.createCanvas(1160, 510);
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

  function drawBox(delay: number, x: number, y: number, w: number, bh: number,
    title: string, subtitle: string | null, active: boolean,
    titleSize = 16, subSize = 12) {
    const fade = p.constrain((localFrame - delay * 6) / 18, 0, 1);
    const yOff = (1 - h.easeOut(fade)) * 14;
    p.push();
    ctx2d(p).globalAlpha = fade;
    h.drawCard(x, y + yOff, w, bh, {
      fill: active ? T.ORANGE_L : T.SURFACE,
      stroke: active ? T.ORANGE : T.BORDER,
      sw: active ? 2 : 1.5,
    });
    const titleY = subtitle ? (y + yOff + bh / 2 - 11) : (y + yOff + bh / 2);
    h.drawText(title, x + w / 2, titleY, {
      size: titleSize, bold: true,
      color: active ? T.ORANGE_D : T.TEXT,
      align: 'center', vAlign: 'center',
    });
    if (subtitle) {
      h.drawText(subtitle, x + w / 2, y + yOff + bh / 2 + 11, {
        size: subSize, color: T.MUTED, italic: true,
        align: 'center', vAlign: 'center',
      });
    }
    p.pop();
  }

  function drawArrow(delay: number, x1: number, y1: number, x2: number, y2: number) {
    const fade = p.constrain((localFrame - delay * 6) / 18, 0, 1);
    p.push();
    ctx2d(p).globalAlpha = fade;
    p.stroke(T.MUTED);
    p.strokeWeight(1.5);
    p.line(x1, y1, x2, y2 - 5);
    p.noStroke();
    p.fill(T.MUTED);
    p.triangle(x2 - 5, y2 - 5, x2 + 5, y2 - 5, x2, y2 + 1);
    p.pop();
  }

  function drawBranch(delay: number, x1: number, y1: number, x2: number, y2: number) {
    const fade = p.constrain((localFrame - delay * 6) / 18, 0, 1);
    p.push();
    ctx2d(p).globalAlpha = fade * 0.85;
    p.stroke(T.MUTED);
    p.strokeWeight(1.5);
    p.noFill();
    const midY = (y1 + y2) / 2;
    p.bezier(x1, y1, x1, midY, x2, midY, x2, y2 - 5);
    p.noStroke();
    p.fill(T.MUTED);
    p.triangle(x2 - 4, y2 - 4, x2 + 4, y2 - 4, x2, y2 + 1);
    p.pop();
  }

  function drawCurvedArrow(delay: number, x1: number, y1: number, x2: number, y2: number, label: string) {
    const fade = p.constrain((localFrame - delay * 6) / 18, 0, 1);
    p.push();
    ctx2d(p).globalAlpha = fade * 0.8;
    p.stroke(T.ORANGE);
    p.strokeWeight(1.5);
    ctx2d(p).setLineDash([5, 4]);
    p.noFill();
    const ctrl1X = x1 + 60, ctrl2X = x2 - 60;
    const ctrlY = (y1 + y2) / 2;
    p.bezier(x1, y1, ctrl1X, ctrlY, ctrl2X, ctrlY, x2, y2);
    ctx2d(p).setLineDash([]);
    p.noStroke();
    p.fill(T.ORANGE);
    p.triangle(x2 - 5, y2 - 4, x2 - 5, y2 + 4, x2 + 1, y2);
    if (label) {
      p.fill(T.ORANGE);
      p.textFont('Noto Serif');
      p.textSize(12);
      p.textStyle(p.ITALIC);
      p.textAlign(p.CENTER, p.CENTER);
      p.text(label, (x1 + x2) / 2, (y1 + y2) / 2 - 12);
    }
    p.pop();
  }

  p.draw = () => {
    p.background(T.BG);
    localFrame++;

    const cx = 580;

    const yTop  = 10;
    const yAPI  = 95;
    const yM3   = 180;
    const yMid  = 285;
    const yData = 410;

    const webW = 280, webH = 60;
    const m4W  = 240, m4H  = 60;
    const webX = cx - webW / 2;
    const m4X  = webX - m4W - 80;

    drawBox(0, m4X, yTop, m4W, m4H, 'Module 4: Mood Classifier', 'optional mood seed', true);
    drawBox(1, webX, yTop, webW, webH, 'React Web UI', 'song picker · playlist results', false);
    drawCurvedArrow(2, m4X + m4W, yTop + m4H / 2, cx - 200, yAPI + 20, 'mood input');
    drawArrow(2, cx, yTop + webH, cx, yAPI);

    const apiW = 460, apiH = 60;
    drawBox(3, cx - apiW / 2, yAPI, apiW, apiH, 'Flask API', '/api/playlist  ·  /api/compare', false);
    drawArrow(4, cx, yAPI + apiH, cx, yM3);

    const m3W = 540, m3H = 70;
    drawBox(5, cx - m3W / 2, yM3, m3W, m3H,
      'Module 3: PlaylistAssembler',
      'orchestrator — runs beam search, scoring, constraints', true);

    const subW = 280, subH = 70;
    const m2X = cx - subW - 30;
    const m1X = cx + 30;

    drawBranch(6, cx - 80, yM3 + m3H, m2X + subW / 2, yMid);
    drawBranch(6, cx + 80, yM3 + m3H, m1X + subW / 2, yMid);

    drawBox(7, m2X, yMid, subW, subH, 'Module 2: Beam Search', 'bidirectional · A* heuristic', true);
    drawBox(8, m1X, yMid, subW, subH, 'Module 1: ProbLog KB', '12-dim compatibility scoring', true);

    const dW = 200, dH = 48;
    const dGap = 14;
    const dTotalW = 3 * dW + 2 * dGap;
    const dStartX = m2X + subW / 2 - dTotalW / 2;

    drawArrow(9, m2X + subW / 2, yMid + subH, m2X + subW / 2, yData - 12);

    p.push();
    ctx2d(p).globalAlpha = p.constrain((localFrame - 9 * 6) / 18, 0, 1);
    p.stroke(T.MUTED);
    p.strokeWeight(1.5);
    p.line(dStartX + dW / 2, yData - 12, dStartX + 2 * (dW + dGap) + dW / 2, yData - 12);
    p.pop();

    const sources = [
      ['MusicBrainz', 'Postgres mirror'],
      ['AcousticBrainz', 'audio features'],
      ['ListenBrainz', 'similarity graph'],
    ] as const;

    sources.forEach(([name, sub], i) => {
      const dx = dStartX + i * (dW + dGap);
      p.push();
      ctx2d(p).globalAlpha = p.constrain((localFrame - (10 + i) * 6) / 18, 0, 1);
      p.stroke(T.MUTED);
      p.strokeWeight(1.5);
      p.line(dx + dW / 2, yData - 12, dx + dW / 2, yData);
      p.pop();
      drawBox(10 + i, dx, yData, dW, dH, name, sub, false, 13, 11);
    });

    if (localFrame > 14 * 6 + 30) p.noLoop();
  };
};
