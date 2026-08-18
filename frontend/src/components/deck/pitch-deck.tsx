import { useCallback, useEffect, useState } from "react";
import { ChevronLeft, ChevronRight, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { PITCH_SLIDES } from "@/components/deck/slides";
import { cn } from "@/lib/utils";

interface DeckProps {
  fullscreen?: boolean;
  onExit?: () => void;
}

function DeckBackground() {
  return (
    <div className="pointer-events-none absolute inset-0 -z-10 overflow-hidden" aria-hidden="true">
      <div className="absolute inset-0 bg-gradient-to-br from-indigo-500/[0.07] via-transparent to-fuchsia-500/[0.09]" />
      <div className="animate-drift absolute -left-24 -top-16 h-[26rem] w-[26rem] rounded-full bg-indigo-500/25 blur-3xl" />
      <div
        className="animate-drift absolute -right-24 bottom-0 h-[28rem] w-[28rem] rounded-full bg-fuchsia-500/20 blur-3xl"
        style={{ animationDelay: "-12s" }}
      />
      <div
        className="animate-drift absolute left-1/3 top-1/2 h-72 w-72 rounded-full bg-sky-400/15 blur-3xl"
        style={{ animationDelay: "-20s" }}
      />
    </div>
  );
}

export function Deck({ fullscreen = false, onExit }: DeckProps) {
  const [current, setCurrent] = useState(0);
  const [direction, setDirection] = useState<"forward" | "backward">("forward");
  const total = PITCH_SLIDES.length;

  const go = useCallback(
    (next: number) => {
      const clamped = Math.max(0, Math.min(total - 1, next));
      setDirection(clamped >= current ? "forward" : "backward");
      setCurrent(clamped);
    },
    [current, total]
  );

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const t = e.target as HTMLElement | null;
      if (
        t &&
        (t.tagName === "INPUT" ||
          t.tagName === "TEXTAREA" ||
          (t as HTMLElement).isContentEditable)
      ) {
        return;
      }
      if (e.key === "ArrowRight" || e.key === "PageDown" || e.key === " ") {
        e.preventDefault();
        go(current + 1);
      } else if (e.key === "ArrowLeft" || e.key === "PageUp") {
        e.preventDefault();
        go(current - 1);
      } else if (e.key === "Home") {
        e.preventDefault();
        go(0);
      } else if (e.key === "End") {
        e.preventDefault();
        go(total - 1);
      } else if (e.key === "Escape" && fullscreen && onExit) {
        e.preventDefault();
        onExit();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [current, go, total, fullscreen, onExit]);

  const enterAnim =
    direction === "forward"
      ? "animate-in fade-in slide-in-from-right duration-500"
      : "animate-in fade-in slide-in-from-left duration-500";

  return (
    <div
      className={cn(
        "relative isolate flex flex-col overflow-hidden",
        fullscreen ? "h-dvh" : "h-full"
      )}
    >
      <DeckBackground />

      {fullscreen && onExit && (
        <Button
          variant="secondary"
          size="sm"
          onClick={onExit}
          className="fixed left-4 top-4 z-20 gap-1.5 rounded-full shadow-lg"
          aria-label="Exit presentation"
        >
          <X className="h-4 w-4" />
          Exit
        </Button>
      )}

      {/* progress bar */}
      <div className="shrink-0 px-6 pt-5 md:px-12">
        <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
          <div
            className="h-full rounded-full bg-gradient-to-r from-indigo-500 via-violet-500 to-fuchsia-500 transition-[width] duration-500"
            style={{ width: `${((current + 1) / total) * 100}%` }}
          />
        </div>
      </div>

      {/* slide area */}
      <div className="relative min-h-0 flex-1">
        <div key={current} className={cn("absolute inset-0 overflow-y-auto", enterAnim)}>
          {PITCH_SLIDES[current].render()}
        </div>
      </div>

      {/* controls */}
      <div className="flex shrink-0 items-center justify-between gap-4 px-6 py-4 md:px-12">
        <span className="font-mono text-xs tabular-nums text-muted-foreground">
          {String(current + 1).padStart(2, "0")} / {String(total).padStart(2, "0")}
        </span>

        <div className="flex items-center gap-1.5">
          {PITCH_SLIDES.map((s, i) => (
            <button
              key={s.id}
              onClick={() => go(i)}
              aria-label={`Go to slide ${i + 1}: ${s.label}`}
              aria-current={i === current ? "true" : undefined}
              title={s.label}
              className={cn(
                "h-2 rounded-full transition-all duration-300",
                i === current
                  ? "w-6 bg-primary"
                  : "w-2 bg-muted-foreground/25 hover:bg-muted-foreground/50"
              )}
            />
          ))}
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="icon"
            className="h-8 w-8 rounded-full"
            onClick={() => go(current - 1)}
            disabled={current === 0}
            aria-label="Previous slide"
          >
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <Button
            variant="outline"
            size="icon"
            className="h-8 w-8 rounded-full"
            onClick={() => go(current + 1)}
            disabled={current === total - 1}
            aria-label="Next slide"
          >
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}
