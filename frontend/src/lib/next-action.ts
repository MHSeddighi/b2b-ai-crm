/**
 * Parses the LLM-generated «اقدام بعدی» text into structured fields.
 *
 * The generator (backend/agents/intel_summary.py) is instructed to emit a
 * fixed four-line shape:
 *
 *   اقدام اصلی: <action name>
 *   چرا الان: <evidence from signals>
 *   گام بعدی: <concrete next step>
 *   اولویت: <بالا | متوسط | کم>
 *
 * The parser is defensive: any missing or reordered line degrades gracefully
 * (empty string), and unparseable text returns null so the caller can fall
 * back to rendering the raw text.
 */
export interface ParsedNextAction {
  action: string;
  why: string;
  nextStep: string;
  priority: "بالا" | "متوسط" | "کم" | "نامشخص";
  raw: string;
}

const PRIORITIES = new Set(["بالا", "متوسط", "کم"]);

export function parseNextAction(text: string): ParsedNextAction | null {
  if (!text) return null;
  const lines = text
    .split("\n")
    .map((l) => l.trim())
    .filter(Boolean);

  const pick = (prefix: string): string => {
    const line = lines.find((l) => l.startsWith(prefix));
    return line ? line.slice(prefix.length).trim() : "";
  };

  const action = pick("اقدام اصلی:");
  const why = pick("چرا الان:");
  const nextStep = pick("گام بعدی:");
  const rawPriority = pick("اولویت:");
  const priority: ParsedNextAction["priority"] =
    rawPriority && PRIORITIES.has(rawPriority)
      ? (rawPriority as ParsedNextAction["priority"])
      : "نامشخص";

  if (!action && !why && !nextStep) return null;
  return { action, why, nextStep, priority, raw: text };
}
