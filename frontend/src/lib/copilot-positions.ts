export type CopilotPosition =
  | "nw"
  | "n"
  | "ne"
  | "e"
  | "se"
  | "s"
  | "sw"
  | "w";

export const COPILOT_POSITIONS: CopilotPosition[] = [
  "nw",
  "n",
  "ne",
  "w",
  "e",
  "sw",
  "s",
  "se",
];

/** 3x3 grid for the position picker; the center cell is a decorative placeholder. */
export const POSITION_GRID: (CopilotPosition | null)[][] = [
  ["nw", "n", "ne"],
  ["w", null, "e"],
  ["sw", "s", "se"],
];

/** Fixed positioning for the FAB launcher cluster. */
export const FAB_POSITION_CLASS: Record<CopilotPosition, string> = {
  nw: "top-2 left-2 md:top-3 md:left-3",
  n: "top-2 left-1/2 -translate-x-1/2 md:top-3",
  ne: "top-2 right-2 md:top-3 md:right-3",
  e: "right-2 top-1/2 -translate-y-1/2 md:right-3",
  se: "bottom-2 right-2 md:bottom-3 md:right-3",
  s: "bottom-2 left-1/2 -translate-x-1/2 md:bottom-3",
  sw: "bottom-2 left-2 md:bottom-3 md:left-3",
  w: "left-2 top-1/2 -translate-y-1/2 md:left-3",
};

/**
 * Fixed positioning for the floating copilot window.
 * Centered positions use margin-auto centering (inset-x-0 mx-auto / inset-y-0 my-auto)
 * instead of transforms, so they don't fight the entrance zoom animation.
 */
export const PANEL_POSITION_CLASS: Record<CopilotPosition, string> = {
  nw: "top-2 left-2 md:top-3 md:left-3",
  n: "top-2 inset-x-0 mx-auto md:top-3",
  ne: "top-2 right-2 md:top-3 md:right-3",
  e: "inset-y-0 my-auto right-2 md:right-3",
  se: "bottom-2 right-2 md:bottom-3 md:right-3",
  s: "bottom-2 inset-x-0 mx-auto md:bottom-3",
  sw: "bottom-2 left-2 md:bottom-3 md:left-3",
  w: "inset-y-0 my-auto left-2 md:left-3",
};

/** Return the position (snap target) closest to the given viewport point. */
export function nearestCopilotPosition(x: number, y: number): CopilotPosition {
  const inset = 12;
  const w = window.innerWidth;
  const h = window.innerHeight;
  const anchors: { pos: CopilotPosition; x: number; y: number }[] = [
    { pos: "nw", x: inset, y: inset },
    { pos: "n", x: w / 2, y: inset },
    { pos: "ne", x: w - inset, y: inset },
    { pos: "e", x: w - inset, y: h / 2 },
    { pos: "se", x: w - inset, y: h - inset },
    { pos: "s", x: w / 2, y: h - inset },
    { pos: "sw", x: inset, y: h - inset },
    { pos: "w", x: inset, y: h / 2 },
  ];
  let best = anchors[0];
  let bestDist = Infinity;
  for (const a of anchors) {
    const d = (a.x - x) ** 2 + (a.y - y) ** 2;
    if (d < bestDist) {
      bestDist = d;
      best = a;
    }
  }
  return best.pos;
}
