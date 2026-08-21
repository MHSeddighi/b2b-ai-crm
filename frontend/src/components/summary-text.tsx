import { cn } from "@/lib/utils";

/**
 * Renders the LLM intelligence summaries (dashboard "تحلیل کلی هوشمند" and
 * customer "خلاصه هوشمند") as clean, scannable text.
 *
 * The LLM output is free-form Persian that may include:
 *   - `### ` / `## ` / `# ` markdown section headings (e.g. "### وضعیت کلی")
 *   - `**label**` emphasis (e.g. "**وضعیت کلی**")
 *   - plain label lines ending in ":" (e.g. "وضعیت کلی:")
 *   - "- " / "• " bullet lines
 *
 * Headings are rendered as section headers, bullets as bulleted rows, and no
 * punctuation is force-appended — text is shown exactly as written, so the
 * summary never looks like raw markdown and no stray dots are injected.
 */
export function SummaryText({ text, className }: { text: string; className?: string }) {
  const lines = text.split("\n").filter((l) => l.trim() !== "");
  return (
    <div className={cn("space-y-2", className)}>
      {lines.map((line, i) => {
        const trimmed = line.trim();

        // Markdown headings: "### وضعیت کلی" / "## ..." / "# ..."
        const mdHeading = trimmed.match(/^#{1,3}\s+(.+)$/);
        if (mdHeading) {
          return (
            <p key={i} className="pt-1 text-sm font-semibold">
              {mdHeading[1].replace(/\*\*/g, "").trim()}
            </p>
          );
        }

        // Bold heading: "**وضعیت کلی**"
        if (/^\*\*.+\*\*$/.test(trimmed)) {
          return (
            <p key={i} className="pt-1 text-sm font-semibold">
              {trimmed.replace(/\*\*/g, "")}
            </p>
          );
        }

        // Short label ending in ":" — "وضعیت کلی:" / "نکات مهم:"
        if (/^[^.!?]{2,40}:$/.test(trimmed)) {
          return (
            <p key={i} className="pt-1 text-sm font-semibold">
              {trimmed.replace(/\*\*/g, "")}
            </p>
          );
        }

        const body = trimmed.replace(/\*\*/g, "");
        if (body.startsWith("- ") || body.startsWith("• ")) {
          return (
            <p key={i} className="flex items-start gap-1.5 text-sm leading-relaxed text-foreground/90">
              <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-primary/70" />
              <span>{body.replace(/^[-•]\s*/, "")}</span>
            </p>
          );
        }
        return (
          <p key={i} className="text-sm leading-relaxed text-foreground/90">
            {body}
          </p>
        );
      })}
    </div>
  );
}
