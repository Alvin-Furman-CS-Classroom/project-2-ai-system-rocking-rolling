import type { P5CanvasInstance, Sketch, SketchProps } from "@p5-wrapper/react";
import { ctx2d } from "../p5helpers";
import { T } from "../theme";

// Full slide canvas dimensions
const WC = 1280,
  HC = 720;
// Node layout region — nodes stay centered in this inner area
const W = 1100,
  H = 420;
const OX = (WC - W) / 2; // 90 — horizontal offset into canvas
const OY = (HC - H) / 2; // 150 — vertical offset into canvas

type Props = SketchProps & {
  isActive: boolean;
  replayKey: number;
  startTitle: string;
  startArtist: string;
  endTitle: string;
  endArtist: string;
};

function truncate(s: string, max: number): string {
  return s.length > max ? s.slice(0, max - 1) + "…" : s;
}

export const demoBeamSearchSketch: Sketch<Props> = (
  p: P5CanvasInstance<Props>,
) => {
  let frame = 0;
  const totalFrames = 520;
  let nodes: { x: number; y: number }[] = [];
  let nodeCols: number[] = [];
  let nodeRows: number[] = [];
  let edges: [number, number][] = [];
  let path: { x: number; y: number }[] = [];
  let wasActive = false;
  let lastReplayKey = 0;
  let startTitle = "";
  let startArtist = "";
  let endTitle = "";
  let endArtist = "";

  function generateGraph() {
    let s = 42;
    const rand = () => {
      s = (s * 16807) % 2147483647;
      return (s - 1) / 2147483646;
    };

    const source = { x: OX + 60, y: HC / 2 };
    const dest = { x: OX + W - 60, y: HC / 2 };
    nodes = [source, dest];
    nodeCols = [0, 8];
    nodeRows = [-1, -1]; // endpoints connect to all rows in the adjacent column

    for (let col = 1; col <= 7; col++) {
      const cx = (col / 8) * W;
      for (let r = 0; r < 4; r++) {
        nodes.push({
          x: OX + cx + (rand() - 0.5) * 80,
          y: OY + 35 + r * 110 + (rand() - 0.5) * 40,
        });
        nodeCols.push(col);
        nodeRows.push(r);
      }
    }

    // Connect nodes in adjacent columns only if their rows are also adjacent (±1).
    // Endpoints (row -1) connect to all rows in the neighbouring column.
    edges = [];
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        if (Math.abs(nodeCols[j] - nodeCols[i]) !== 1) continue;
        const ri = nodeRows[i],
          rj = nodeRows[j];
        if (ri === -1 || rj === -1 || Math.abs(ri - rj) <= 1)
          edges.push([i, j]);
      }
    }

    path = [source];
    for (let col = 1; col <= 7; col++) {
      const cx = (col / 8) * W;
      let best: { x: number; y: number } | null = null,
        bestD = 1e9;
      nodes.forEach((n) => {
        const dx = Math.abs(n.x - (OX + cx));
        if (dx < 80) {
          const d = Math.abs(n.y - HC / 2) * 0.8 + dx;
          if (d < bestD) {
            bestD = d;
            best = n;
          }
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

  function drawEndpointLabel(
    x: number,
    y: number,
    title: string,
    artist: string,
    color: string,
  ) {
    p.noStroke();
    p.textFont("Noto Serif");
    p.textAlign(p.CENTER, p.TOP);
    p.textStyle(p.BOLD);
    p.textSize(12);
    p.fill(color);
    p.text(truncate(title, 18), x, y + 18);
    p.textStyle(p.NORMAL);
    p.textSize(11);
    p.fill(T.MUTED);
    p.text(truncate(artist, 20), x, y + 33);
  }

  p.setup = () => {
    p.createCanvas(WC, HC);
    p.textFont("Noto Serif");
enter();
  };

  p.updateWithProps = (props: Props) => {
    startTitle = props.startTitle;
    startArtist = props.startArtist;
    endTitle = props.endTitle;
    endArtist = props.endArtist;

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
    frame = (frame + 1) % totalFrames;

    // Edges (faint)
    p.stroke(T.BORDER);
    p.strokeWeight(1);
    edges.forEach(([i, j]) => {
      p.line(nodes[i].x, nodes[i].y, nodes[j].x, nodes[j].y);
    });

    const source = nodes[0];
    const dest = nodes[1];
    const maxR = WC * 0.75;

    // Path line (drawn early so nodes render on top)
    if (frame >= 260) {
      const pathFrame = frame - 260;
      const progress = Math.min(pathFrame / 180, 1);
      const segCount = Math.floor(progress * (path.length - 1));
      const segFrac = progress * (path.length - 1) - segCount;

      p.stroke(T.ORANGE);
      p.strokeWeight(4);
      p.noFill();
      p.beginShape();
      p.vertex(path[0].x, path[0].y);
      for (let i = 1; i <= segCount && i < path.length; i++) {
        p.vertex(path[i].x, path[i].y);
      }
      if (segCount < path.length - 1) {
        const from = path[segCount],
          to = path[segCount + 1];
        p.vertex(
          from.x + (to.x - from.x) * segFrac,
          from.y + (to.y - from.y) * segFrac,
        );
      }
      p.endShape();

      // Intermediate path dots (not endpoints)
      p.noStroke();
      p.fill(T.ORANGE);
      for (let i = 1; i < Math.min(segCount, path.length - 1); i++) {
        p.circle(path[i].x, path[i].y, 16);
      }
    }

    if (frame <= 320) {
      const fwdR = Math.min(frame * 2, maxR);
      const bwdR = Math.min(Math.max(frame - 24, 0) * 2, maxR);

      for (let k = 0; k < 3; k++) {
        const rOff = k * 25;
        const ringR1 = fwdR - rOff;
        const ringR2 = bwdR - rOff;
        if (ringR1 > 0) {
          p.stroke(T.ORANGE);
          p.strokeWeight(1.5);
          p.noFill();
          ctx2d(p).globalAlpha = 0.15 - k * 0.04;
          p.circle(source.x, source.y, ringR1 * 2);
        }
        if (ringR2 > 0) {
          p.stroke(T.TEXT);
          p.strokeWeight(1.5);
          p.noFill();
          ctx2d(p).globalAlpha = 0.15 - k * 0.04;
          p.circle(dest.x, dest.y, ringR2 * 2);
        }
      }
      ctx2d(p).globalAlpha = 1;

      edges.forEach(([i, j]) => {
        const ni = nodes[i],
          nj = nodes[j];
        const dSi = Math.hypot(ni.x - source.x, ni.y - source.y);
        const dSj = Math.hypot(nj.x - source.x, nj.y - source.y);
        const dDi = Math.hypot(ni.x - dest.x, ni.y - dest.y);
        const dDj = Math.hypot(nj.x - dest.x, nj.y - dest.y);

        if (dSi < fwdR && dSj < fwdR) {
          p.stroke(T.ORANGE);
          p.strokeWeight(1.5);
          ctx2d(p).globalAlpha = 0.4;
          p.line(ni.x, ni.y, nj.x, nj.y);
        }
        if (dDi < bwdR && dDj < bwdR) {
          p.stroke(T.TEXT);
          p.strokeWeight(1.5);
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
        p.noStroke();
        p.fill(c);
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
        p.noStroke();
        p.fill(c);
        ctx2d(p).globalAlpha = i < 2 ? 1 : 0.4;
        p.circle(n.x, n.y, i < 2 ? 28 : 16);
        ctx2d(p).globalAlpha = 1;
      });
    }

    // Endpoint labels (always on top)
    drawEndpointLabel(source.x, source.y, startTitle, startArtist, T.ORANGE);
    drawEndpointLabel(dest.x, dest.y, endTitle, endArtist, T.TEXT);
  };
};
