import type { P5CanvasInstance, Sketch, SketchProps } from "@p5-wrapper/react";
import type { ThemeHelpers } from "../p5helpers";
import { createThemeHelpers, ctx2d } from "../p5helpers";
import { T } from "../theme";

type Props = SketchProps & { isActive: boolean; replayKey: number };

export const architectureSketch: Sketch<Props> = (
  p: P5CanvasInstance<Props>,
) => {
  let h: ThemeHelpers;
  let localFrame = 0;
  let wasActive = false;
  let lastReplayKey = 0;

  function enter() {
    localFrame = 0;
  }

  p.setup = () => {
    p.createCanvas(1160, 510);
    p.textFont("Noto Serif");
    h = createThemeHelpers(p);
    enter();
  };

  p.updateWithProps = (props: Props) => {
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

  function drawBox(
    delay: number,
    x: number,
    y: number,
    w: number,
    bh: number,
    title: string,
    subtitle: string | null,
    active: boolean,
    titleSize = 18,
    subSize = 13,
  ) {
    const fade = p.constrain((localFrame - delay * 6) / 18, 0, 1);
    const yOff = (1 - h.easeOut(fade)) * 14;
    p.push();
    ctx2d(p).globalAlpha = fade;
    h.drawCard(x, y + yOff, w, bh, {
      fill: active ? T.ORANGE_L : T.SURFACE,
      stroke: active ? T.ORANGE : T.BORDER,
      sw: active ? 2 : 1.5,
    });
    const titleY = subtitle ? y + yOff + bh / 2 - 11 : y + yOff + bh / 2;
    h.drawText(title, x + w / 2, titleY, {
      size: titleSize,
      bold: true,
      color: active ? T.ORANGE_D : T.TEXT,
      align: "center",
      vAlign: "center",
    });
    if (subtitle) {
      h.drawText(subtitle, x + w / 2, y + yOff + bh / 2 + 11, {
        size: subSize,
        color: T.MUTED,
        italic: true,
        align: "center",
        vAlign: "center",
      });
    }
    p.pop();
  }

  function drawArrow(
    delay: number,
    x1: number,
    y1: number,
    x2: number,
    y2: number,
  ) {
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

  function drawBranch(
    delay: number,
    x1: number,
    y1: number,
    x2: number,
    y2: number,
  ) {
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

  p.draw = () => {
    p.background(T.BG);
    localFrame++;

    const cx = 580;

    const yTop = 20;
    const yAPI = 154;
    const yM3 = 288;
    const yMid = 430;

    const webW = 280,
      webH = 72;
    const webX = cx - webW / 2;

    drawBox(
      0,
      webX,
      yTop,
      webW,
      webH,
      "React Web UI",
      "song picker · playlist results",
      false,
    );
    drawArrow(1, cx, yTop + webH, cx, yAPI);

    const apiW = 460,
      apiH = 72;
    drawBox(
      2,
      cx - apiW / 2,
      yAPI,
      apiW,
      apiH,
      "Flask API",
      "/api/playlist  ·  /api/compare",
      false,
    );

    // M3 + M4 pair centered at cx
    const m3W = 380,
      m3H = 80;
    const m4W = 260,
      m4H = 80;
    const pairW = m3W + 20 + m4W;
    const m3X = cx - pairW / 2;
    const m4X = m3X + m3W + 20;

    drawBranch(3, cx - 20, yAPI + apiH, m3X + m3W / 2, yM3);
    drawBranch(3, cx + 20, yAPI + apiH, m4X + m4W / 2, yM3);

    drawBox(
      4,
      m3X,
      yM3,
      m3W,
      m3H,
      "Module 3: PlaylistAssembler",
      "orchestrator — runs beam search, scoring, constraints",
      true,
    );
    drawBox(
      4,
      m4X,
      yM3,
      m4W,
      m4H,
      "Module 4: Mood Classifier",
      "optional mood seed",
      true,
    );

    const subW = 280,
      subH = 80;
    const m3CX = m3X + m3W / 2;
    const m1X = m3CX - subW - 10;
    const m2X = m3CX + 10;

    drawBranch(5, m3X + m3W * 0.3, yM3 + m3H, m1X + subW / 2, yMid);
    drawBranch(5, m3X + m3W * 0.7, yM3 + m3H, m2X + subW / 2, yMid);

    drawBox(
      6,
      m1X,
      yMid,
      subW,
      subH,
      "Module 1: ProbLog KB",
      "12-dim compatibility scoring",
      true,
    );
    drawBox(
      7,
      m2X,
      yMid,
      subW,
      subH,
      "Module 2: Beam Search",
      "bidirectional · A* heuristic",
      true,
    );

    if (localFrame > 7 * 6 + 30) p.noLoop();
  };
};
