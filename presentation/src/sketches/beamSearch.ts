import type { P5CanvasInstance, Sketch, SketchProps } from '@p5-wrapper/react';
import type { ThemeHelpers } from '../p5helpers';
import { createThemeHelpers, ctx2d } from '../p5helpers';
import { T } from '../theme';

const W = 1100, H = 460;

type Props = SketchProps & { isActive: boolean; replayKey: number };

export const beamSearchSketch: Sketch<Props> = (p: P5CanvasInstance<Props>) => {
  let h: ThemeHelpers;
  let frame = 0;
  const totalFrames = 240;
  let nodes: { x: number; y: number }[] = [];
  let edges: [number, number][] = [];
  let path: { x: number; y: number }[] = [];
  let wasActive = false;
  let lastReplayKey = 0;

  function generateGraph() {
    let s = 42;
    const rand = () => { s = (s * 16807) % 2147483647; return (s - 1) / 2147483646; };

    const source = { x: 60, y: H / 2 };
    const dest   = { x: W - 60, y: H / 2 };
    nodes = [source, dest];

    for (let col = 1; col <= 7; col++) {
      const cx = (col / 8) * W;
      for (let r = 0; r < 4; r++) {
        nodes.push({ x: cx + (rand() - 0.5) * 70, y: 50 + r * 120 + (rand() - 0.5) * 50 });
      }
    }

    edges = [];
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        const dx = nodes[i].x - nodes[j].x;
        const dy = nodes[i].y - nodes[j].y;
        if (Math.sqrt(dx * dx + dy * dy) < 200) edges.push([i, j]);
      }
    }

    path = [source];
    for (let col = 1; col <= 7; col++) {
      const cx = (col / 8) * W;
      let best: { x: number; y: number } | null = null, bestD = 1e9;
      nodes.forEach(n => {
        const dx = Math.abs(n.x - cx);
        if (dx < 80) {
          const d = Math.abs(n.y - H / 2) * 0.8 + dx;
          if (d < bestD) { bestD = d; best = n; }
        }
      });
      if (best) path.push(best);
    }
    path.push(dest);
  }

  function enter() {
    frame = 0;
    generateGraph();
  }

  p.setup = () => {
    p.createCanvas(W, H);
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
    frame = (frame + 1) % totalFrames;

    h.drawCard(0, 0, W, H, { fill: T.SURFACE });

    // Edges (faint)
    p.stroke(T.BORDER);
    p.strokeWeight(1);
    edges.forEach(([i, j]) => {
      p.line(nodes[i].x, nodes[i].y, nodes[j].x, nodes[j].y);
    });

    const source = nodes[0];
    const dest = nodes[1];
    const maxR = W * 0.55;

    if (frame <= 160) {
      const fwdR = Math.min(frame * 4, maxR);
      const bwdR = Math.min(Math.max(frame - 12, 0) * 4, maxR);

      for (let k = 0; k < 3; k++) {
        const rOff = k * 25;
        const ringR1 = fwdR - rOff;
        const ringR2 = bwdR - rOff;
        if (ringR1 > 0) {
          p.stroke(T.ORANGE); p.strokeWeight(1.5); p.noFill();
          ctx2d(p).globalAlpha = 0.15 - k * 0.04;
          p.circle(source.x, source.y, ringR1 * 2);
        }
        if (ringR2 > 0) {
          p.stroke(T.TEXT); p.strokeWeight(1.5); p.noFill();
          ctx2d(p).globalAlpha = 0.15 - k * 0.04;
          p.circle(dest.x, dest.y, ringR2 * 2);
        }
      }
      ctx2d(p).globalAlpha = 1;

      edges.forEach(([i, j]) => {
        const ni = nodes[i], nj = nodes[j];
        const dSi = Math.hypot(ni.x - source.x, ni.y - source.y);
        const dSj = Math.hypot(nj.x - source.x, nj.y - source.y);
        const dDi = Math.hypot(ni.x - dest.x, ni.y - dest.y);
        const dDj = Math.hypot(nj.x - dest.x, nj.y - dest.y);

        if (dSi < fwdR && dSj < fwdR) {
          p.stroke(T.ORANGE); p.strokeWeight(1.5);
          ctx2d(p).globalAlpha = 0.4;
          p.line(ni.x, ni.y, nj.x, nj.y);
        }
        if (dDi < bwdR && dDj < bwdR) {
          p.stroke(T.TEXT); p.strokeWeight(1.5);
          ctx2d(p).globalAlpha = 0.4;
          p.line(ni.x, ni.y, nj.x, nj.y);
        }
        ctx2d(p).globalAlpha = 1;
      });

      nodes.forEach((n, i) => {
        const dS = Math.hypot(n.x - source.x, n.y - source.y);
        const dD = Math.hypot(n.x - dest.x, n.y - dest.y);
        let c: string = T.MUTED;
        if (i === 0) c = T.ORANGE;
        else if (i === 1) c = T.TEXT;
        else if (dS < fwdR) c = T.ORANGE;
        else if (dD < bwdR) c = T.TEXT;
        p.noStroke(); p.fill(c);
        p.circle(n.x, n.y, i < 2 ? 28 : 16);
      });
    } else {
      nodes.forEach((n, i) => {
        const dS = Math.hypot(n.x - source.x, n.y - source.y);
        const dD = Math.hypot(n.x - dest.x, n.y - dest.y);
        let c: string = T.MUTED;
        if (i === 0) c = T.ORANGE;
        else if (i === 1) c = T.TEXT;
        else if (dS < dD) c = T.ORANGE;
        else c = T.TEXT;
        p.noStroke(); p.fill(c);
        ctx2d(p).globalAlpha = 0.4;
        p.circle(n.x, n.y, i < 2 ? 28 : 16);
        ctx2d(p).globalAlpha = 1;
      });
    }

    // Path drawing phase
    if (frame >= 130) {
      const pathFrame = frame - 130;
      const progress = Math.min(pathFrame / 90, 1);
      const segCount = Math.floor(progress * (path.length - 1));
      const segFrac  = progress * (path.length - 1) - segCount;

      p.stroke(T.ORANGE); p.strokeWeight(4); p.noFill();
      p.beginShape();
      p.vertex(path[0].x, path[0].y);
      for (let i = 1; i <= segCount && i < path.length; i++) {
        p.vertex(path[i].x, path[i].y);
      }
      if (segCount < path.length - 1) {
        const from = path[segCount], to = path[segCount + 1];
        p.vertex(from.x + (to.x - from.x) * segFrac, from.y + (to.y - from.y) * segFrac);
      }
      p.endShape();

      p.noStroke(); p.fill(T.ORANGE);
      for (let i = 0; i <= Math.min(segCount, path.length - 1); i++) {
        p.circle(path[i].x, path[i].y, 14);
      }
    }

    // S/D labels
    p.fill(255); p.noStroke();
    p.textFont('Noto Serif'); p.textSize(15); p.textStyle(p.BOLD);
    p.textAlign(p.CENTER, p.CENTER);
    p.text('S', source.x, source.y);
    p.text('D', dest.x, dest.y);
  };
};
