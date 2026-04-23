import type { P5CanvasInstance, Sketch, SketchProps } from '@p5-wrapper/react';
import type { ThemeHelpers } from '../p5helpers';
import { createThemeHelpers, ctx2d } from '../p5helpers';
import { T } from '../theme';

const W = 1100, H = 460;
const SX = 60, SY = H / 2;
const DX = 1040, DY = H / 2;

// Forward levels expand right from S; backward levels expand left from D.
// Both sides advance simultaneously per phase — 3 phases each, meeting in the middle.
const FWD_X = [200, 340, 480] as const;
const BWD_X = [900, 760, 620] as const; // [0] = nearest D, [2] = inner (closest to center)

const FWD_LEVELS = [
  { init: [65, 155, 235, 325, 410], kept: new Set([0, 2, 4]), lb: [185, 365] },
  { init: [80, 165, 250, 335, 415], kept: new Set([0, 2, 4]), lb: [115, 295] },
  { init: [75, 160, 255, 340, 415], kept: new Set([0, 2, 4]), lb: [200, 315] },
];
const BWD_LEVELS = [
  { init: [75, 160, 240, 325, 405], kept: new Set([0, 2, 4]), lb: [195, 375] },
  { init: [70, 155, 245, 335, 410], kept: new Set([1, 2, 3]), lb: [105, 290] },
  { init: [80, 165, 250, 330, 410], kept: new Set([1, 2, 3]), lb: [120, 300] },
];

// Path: one LB node (FWD1.lb[1]=295) sits on the winning route to show their value
const PATH_PTS = [
  { x: SX,        y: SY },
  { x: FWD_X[0],  y: FWD_LEVELS[0].init[2] },  // 235
  { x: FWD_X[1],  y: FWD_LEVELS[1].lb[1]   },  // 295 (LB node)
  { x: FWD_X[2],  y: FWD_LEVELS[2].init[2] },  // 255
  { x: BWD_X[2],  y: BWD_LEVELS[2].init[2] },  // 250
  { x: BWD_X[1],  y: BWD_LEVELS[1].init[2] },  // 245
  { x: BWD_X[0],  y: BWD_LEVELS[0].init[2] },  // 240
  { x: DX,        y: DY },
] as const;

// Per-phase timing (relative to that phase's start frame)
const INTRO_END = 25;
const EXPAND_T  = 0;
const PRUNE_T   = 40;
const PRUNE_DUR = 22;
const LB_T      = 68;
const LB_DUR    = 28;
const LEVEL_DUR = 102;

// Global keyframes
const CONNECT_T = INTRO_END + 3 * LEVEL_DUR; // frontiers meet → show cross-edges
const PATH_T    = CONNECT_T + 22;
const HOLD_T    = PATH_T + 65;
const TOTAL     = HOLD_T + 65;
const FRAME_SPEED = 0.55; // advance this many logical frames per draw call (~1.8× slower)
const LOOP_DELAY  = 180;  // draw calls to pause at end before restarting (~3 s at 60 fps)

type Props = SketchProps & { isActive: boolean; replayKey: number };

export const frontierWideningSketch: Sketch<Props> = (p: P5CanvasInstance<Props>) => {
  let h: ThemeHelpers;
  let frame = 0;
  let loopDelay = 0;
  let wasActive = false;
  let lastReplayKey = 0;

  function enter() { frame = 0; loopDelay = 0; }

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
    frame = Math.min(frame + FRAME_SPEED, TOTAL);
    h.drawCard(0, 0, W, H, { fill: T.SURFACE });

    const sat = (v: number) => Math.max(0, Math.min(1, v));

    // Frames since the start of the given simultaneous phase (0 or 1)
    function pf(phase: number) { return frame - (INTRO_END + phase * LEVEL_DUR); }

    type LevelDef = { init: number[]; kept: Set<number>; lb: number[] };

    // Alpha of initial node i in a level during the given phase
    function initAlpha(lvl: LevelDef, phase: number, i: number): number {
      const t = pf(phase);
      const popIn = sat((t - EXPAND_T - i * 5) / 8);
      if (popIn === 0) return 0;
      if (!lvl.kept.has(i)) return popIn * (1 - sat((t - PRUNE_T) / PRUNE_DUR));
      return popIn;
    }

    // Alpha of LB node k during the given phase
    function lbAlpha(phase: number, k: number): number {
      return sat((pf(phase) - LB_T - k * 12) / 10);
    }

    // All survivor y-positions for a level (kept init + lb)
    function survivorYs(lvl: LevelDef): number[] {
      const ys: number[] = [];
      lvl.init.forEach((y, i) => { if (lvl.kept.has(i)) ys.push(y); });
      lvl.lb.forEach(y => ys.push(y));
      return ys;
    }

    // Faint edges from each src to target, filtered by y-proximity
    function drawEdges(srcs: { x: number; y: number }[], tx: number, ty: number, alpha: number) {
      if (alpha <= 0) return;
      ctx2d(p).globalAlpha = alpha;
      p.stroke(T.BORDER); p.strokeWeight(1); p.noFill();
      srcs.forEach(src => { if (Math.abs(src.y - ty) < 200) p.line(src.x, src.y, tx, ty); });
      ctx2d(p).globalAlpha = 1;
    }

    // ── Forward edges ──
    // Phase 0: S → FWD0 initial
    FWD_LEVELS[0].init.forEach((y, i) =>
      drawEdges([{ x: SX, y: SY }], FWD_X[0], y, initAlpha(FWD_LEVELS[0], 0, i) * 0.5));
    // Phase 1: FWD0 survivors → FWD1 initial
    {
      const srcs = survivorYs(FWD_LEVELS[0]).map(y => ({ x: FWD_X[0], y }));
      FWD_LEVELS[1].init.forEach((y, i) =>
        drawEdges(srcs, FWD_X[1], y, initAlpha(FWD_LEVELS[1], 1, i) * 0.5));
    }
    // Phase 2: FWD1 survivors → FWD2 initial
    {
      const srcs = survivorYs(FWD_LEVELS[1]).map(y => ({ x: FWD_X[1], y }));
      FWD_LEVELS[2].init.forEach((y, i) =>
        drawEdges(srcs, FWD_X[2], y, initAlpha(FWD_LEVELS[2], 2, i) * 0.5));
    }

    // ── Backward edges ──
    // Phase 0: D → BWD0 initial
    BWD_LEVELS[0].init.forEach((y, i) =>
      drawEdges([{ x: DX, y: DY }], BWD_X[0], y, initAlpha(BWD_LEVELS[0], 0, i) * 0.5));
    // Phase 1: BWD0 survivors → BWD1 initial
    {
      const srcs = survivorYs(BWD_LEVELS[0]).map(y => ({ x: BWD_X[0], y }));
      BWD_LEVELS[1].init.forEach((y, i) =>
        drawEdges(srcs, BWD_X[1], y, initAlpha(BWD_LEVELS[1], 1, i) * 0.5));
    }
    // Phase 2: BWD1 survivors → BWD2 initial
    {
      const srcs = survivorYs(BWD_LEVELS[1]).map(y => ({ x: BWD_X[1], y }));
      BWD_LEVELS[2].init.forEach((y, i) =>
        drawEdges(srcs, BWD_X[2], y, initAlpha(BWD_LEVELS[2], 2, i) * 0.5));
    }

    // ── Meeting edges: FWD2 survivors ↔ BWD2 survivors ──
    {
      const connectA = sat((frame - CONNECT_T) / 20) * 0.45;
      if (connectA > 0) {
        const fwdSrcs = survivorYs(FWD_LEVELS[2]).map(y => ({ x: FWD_X[2], y }));
        survivorYs(BWD_LEVELS[2]).forEach(by =>
          drawEdges(fwdSrcs, BWD_X[2], by, connectA));
      }
    }

    // ── LB dashed arcs (vertical, from badge bottom down to each new node) ──
    for (let phase = 0; phase < 3; phase++) {
      const t = pf(phase);
      if (t < LB_T) continue;
      // Forward side arcs (orange)
      FWD_LEVELS[phase].lb.forEach((y, k) => {
        const age = t - LB_T - k * 12;
        if (age < 0 || age > 20) return;
        const a = (1 - age / 20) * sat(age / 3) * 0.65;
        ctx2d(p).globalAlpha = a;
        p.stroke(T.ORANGE); p.strokeWeight(1.5); p.noFill();
        ctx2d(p).setLineDash([4, 4]);
        p.line(FWD_X[phase], 36, FWD_X[phase], y);
        ctx2d(p).setLineDash([]);
        ctx2d(p).globalAlpha = 1;
      });
      // Backward side arcs (dark)
      BWD_LEVELS[phase].lb.forEach((y, k) => {
        const age = t - LB_T - k * 12;
        if (age < 0 || age > 20) return;
        const a = (1 - age / 20) * sat(age / 3) * 0.65;
        ctx2d(p).globalAlpha = a;
        p.stroke(T.TEXT); p.strokeWeight(1.5); p.noFill();
        ctx2d(p).setLineDash([4, 4]);
        p.line(BWD_X[phase], 36, BWD_X[phase], y);
        ctx2d(p).setLineDash([]);
        ctx2d(p).globalAlpha = 1;
      });
    }

    // ── Path line (drawn under nodes) ──
    if (frame >= PATH_T) {
      const progress = sat((frame - PATH_T) / 65);
      const pts = PATH_PTS;
      const segCount = Math.floor(progress * (pts.length - 1));
      const segFrac  = progress * (pts.length - 1) - segCount;
      p.stroke(T.ORANGE); p.strokeWeight(4); p.noFill();
      p.beginShape();
      p.vertex(pts[0].x, pts[0].y);
      for (let i = 1; i <= segCount && i < pts.length; i++) p.vertex(pts[i].x, pts[i].y);
      if (segCount < pts.length - 1) {
        const from = pts[segCount], to = pts[segCount + 1];
        p.vertex(from.x + (to.x - from.x) * segFrac, from.y + (to.y - from.y) * segFrac);
      }
      p.endShape();
      p.noStroke(); p.fill(T.ORANGE);
      for (let i = 1; i < Math.min(segCount, pts.length - 1); i++) p.circle(pts[i].x, pts[i].y, 16);
    }

    // ── Forward nodes (orange) ──
    for (let phase = 0; phase < 3; phase++) {
      const lvl = FWD_LEVELS[phase];
      const x = FWD_X[phase];
      lvl.init.forEach((y, i) => {
        const a = initAlpha(lvl, phase, i);
        if (a <= 0) return;
        const pruning = !lvl.kept.has(i) ? sat((pf(phase) - PRUNE_T) / PRUNE_DUR) : 0;
        ctx2d(p).globalAlpha = a;
        p.noStroke(); p.fill(pruning > 0.05 ? T.MUTED : T.ORANGE);
        p.circle(x, y, 14 - pruning * 5);
        ctx2d(p).globalAlpha = 1;
      });
      lvl.lb.forEach((y, k) => {
        const a = lbAlpha(phase, k);
        if (a <= 0) return;
        ctx2d(p).globalAlpha = a;
        p.stroke(255); p.strokeWeight(2); p.fill(T.ORANGE);
        p.circle(x, y, 14);
        ctx2d(p).globalAlpha = 1;
      });
    }

    // ── Backward nodes (dark) ──
    for (let phase = 0; phase < 3; phase++) {
      const lvl = BWD_LEVELS[phase];
      const x = BWD_X[phase];
      lvl.init.forEach((y, i) => {
        const a = initAlpha(lvl, phase, i);
        if (a <= 0) return;
        const pruning = !lvl.kept.has(i) ? sat((pf(phase) - PRUNE_T) / PRUNE_DUR) : 0;
        ctx2d(p).globalAlpha = a;
        p.noStroke(); p.fill(pruning > 0.05 ? T.MUTED : T.TEXT);
        p.circle(x, y, 14 - pruning * 5);
        ctx2d(p).globalAlpha = 1;
      });
      lvl.lb.forEach((y, k) => {
        const a = lbAlpha(phase, k);
        if (a <= 0) return;
        ctx2d(p).globalAlpha = a;
        p.stroke(255); p.strokeWeight(2); p.fill(T.TEXT);
        p.circle(x, y, 14);
        ctx2d(p).globalAlpha = 1;
      });
    }

    // ── S and D (fade in during intro) ──
    const introA = sat(frame / INTRO_END);
    ctx2d(p).globalAlpha = introA;
    p.noStroke(); p.fill(T.ORANGE); p.circle(SX, SY, 28);
    p.noStroke(); p.fill(T.TEXT);   p.circle(DX, DY, 28);
    ctx2d(p).globalAlpha = 1;

    // ── ListenBrainz badges: one per side per phase, appear simultaneously ──
    for (let phase = 0; phase < 3; phase++) {
      const t = pf(phase);
      if (t < LB_T) continue;
      const age = t - LB_T;
      const a = sat(age / 12) * (1 - sat((age - LB_DUR) / 18));
      if (a <= 0) continue;
      ctx2d(p).globalAlpha = a;
      p.textFont('Noto Serif'); p.textSize(11); p.textStyle(p.BOLD);
      p.textAlign(p.CENTER, p.CENTER);
      for (const bx of [FWD_X[phase] - 62, BWD_X[phase] - 62]) {
        p.fill(T.ORANGE_L); p.stroke(T.ORANGE); p.strokeWeight(1.5);
        p.rect(bx, 6, 124, 26, 5);
        p.noStroke(); p.fill(T.ORANGE);
        p.text('ListenBrainz', bx + 62, 19);
      }
      ctx2d(p).globalAlpha = 1;
    }

    // ── S/D labels (always on top) ──
    ctx2d(p).globalAlpha = introA;
    p.fill(255); p.noStroke();
    p.textFont('Noto Serif'); p.textSize(15); p.textStyle(p.BOLD);
    p.textAlign(p.CENTER, p.CENTER);
    p.text('S', SX, SY);
    p.text('D', DX, DY);
    ctx2d(p).globalAlpha = 1;

    if (frame >= TOTAL) {
      if (++loopDelay >= LOOP_DELAY) enter();
    }
  };
};
