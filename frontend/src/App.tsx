import {
  useEffect,
  useRef,
  useState,
  type PointerEvent as ReactPointerEvent,
} from "react";
import { Menu, Sparkles } from "lucide-react";

import { Button } from "@/components/ui/button";
import { ThemeProvider } from "@/components/theme-provider";
import { Sidebar, type View } from "@/components/sidebar";
import { Dashboard } from "@/components/dashboard";
import { Customers } from "@/components/customers";
import { Analyses } from "@/components/analyses";
import { Copilot, type CopilotMode } from "@/components/copilot";
import { AppBackground } from "@/components/app-background";
import { Deck } from "@/components/deck/pitch-deck";
import {
  FAB_POSITION_CLASS,
  PANEL_POSITION_CLASS,
  nearestCopilotPosition,
  type CopilotPosition,
} from "@/lib/copilot-positions";
import { cn } from "@/lib/utils";

function AppShell() {
  const [view, setView] = useState<View>(() => {
    const route = window.location.hash.replace("#/", "");
    return route === "present" ? "present" : "dashboard";
  });
  const [copilotOpen, setCopilotOpen] = useState(false);
  const [copilotMode, setCopilotMode] = useState<CopilotMode>("float");
  const [copilotPosition, setCopilotPosition] = useState<CopilotPosition>("sw");

  // Stable backend session id; reset to start a fresh chat thread. Changing it
  // recreates the assistant-ui runtime (which owns the message history), so the
  // "new chat" action just mints a new id.
  const [copilotSessionId, setCopilotSessionId] = useState(() =>
    crypto.randomUUID()
  );

  function startNewChat() {
    setCopilotSessionId(crypto.randomUUID());
  }
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const [dragging, setDragging] = useState(false);
  const [dragPoint, setDragPoint] = useState<{ x: number; y: number } | null>(null);
  const dragRef = useRef({
    startX: 0,
    startY: 0,
    offX: 0,
    offY: 0,
    moved: false,
    justDragged: false,
  });

  const docked = copilotOpen && copilotMode === "dock";

  useEffect(() => {
    const hash = view === "present" ? "#/present" : "#";
    if (window.location.hash !== hash) history.replaceState(null, "", hash);
  }, [view]);

  function onPointerDown(e: ReactPointerEvent<HTMLDivElement>) {
    if (e.button !== 0) return;
    const el = e.currentTarget;
    const rect = el.getBoundingClientRect();
    dragRef.current = {
      startX: e.clientX,
      startY: e.clientY,
      offX: e.clientX - (rect.left + rect.width / 2),
      offY: e.clientY - (rect.top + rect.height / 2),
      moved: false,
      justDragged: false,
    };
    el.setPointerCapture(e.pointerId);
    setDragging(true);
    setDragPoint({ x: e.clientX - dragRef.current.offX, y: e.clientY - dragRef.current.offY });
  }

  function onPointerMove(e: ReactPointerEvent<HTMLDivElement>) {
    if (!dragging) return;
    if (
      Math.hypot(e.clientX - dragRef.current.startX, e.clientY - dragRef.current.startY) > 5
    ) {
      dragRef.current.moved = true;
    }
    setDragPoint({ x: e.clientX - dragRef.current.offX, y: e.clientY - dragRef.current.offY });
  }

  function onPointerUp(e: ReactPointerEvent<HTMLDivElement>) {
    if (!dragging) return;
    const x = e.clientX - dragRef.current.offX;
    const y = e.clientY - dragRef.current.offY;
    if (dragRef.current.moved) {
      dragRef.current.justDragged = true;
      setCopilotPosition(nearestCopilotPosition(x, y));
    }
    setDragging(false);
    setDragPoint(null);
  }

  if (view === "present") {
    return (
      <div className="h-full w-full bg-background text-foreground">
        <Deck fullscreen onExit={() => setView("dashboard")} />
      </div>
    );
  }

  return (
    <div className="relative isolate flex h-full gap-2 overflow-hidden bg-background p-2 text-foreground md:gap-3 md:p-3">
      <AppBackground />

      <Sidebar
        view={view}
        onNavigate={setView}
        mobileOpen={mobileMenuOpen}
        onCloseMobile={() => setMobileMenuOpen(false)}
        collapsed={sidebarCollapsed}
        onToggleCollapsed={() => setSidebarCollapsed((v) => !v)}
      />

      {!docked && (
        <main className="flex min-w-0 flex-1 flex-col">
          <div className="min-h-0 flex-1 overflow-y-auto">
            {view === "dashboard" && <Dashboard />}
            {view === "customers" && <Customers />}
            {view === "analyses" && <Analyses />}
          </div>
        </main>
      )}

      {/* Mobile navigation trigger (header removed) */}
      {!docked && (
        <Button
          variant="secondary"
          size="icon"
          onClick={() => setMobileMenuOpen(true)}
          aria-label="باز کردن منو"
          className="fixed left-2 top-2 z-40 rounded-full shadow-md md:hidden"
        >
          <Menu className="h-5 w-5" />
        </Button>
      )}

      {/* Copilot: one persistent instance; only its container switches between
          docked (full-height panel next to the sidebar) and floating window.
          Keeping the same mounted <Copilot> preserves the chat thread/state
          when the user expands or collapses it. */}
      {copilotOpen && (
        <aside
          aria-label="دستیار هوشمند"
          className={cn(
            "z-50 flex flex-col overflow-hidden",
            docked
              ? "fixed inset-0 p-2 md:p-3 lg:static lg:z-auto lg:flex-1 lg:animate-none lg:p-0"
              : cn(
                  "fixed",
                  "h-[min(680px,calc(100vh-1rem))] w-[min(420px,calc(100vw-1rem))]",
                  "md:h-[min(680px,calc(100vh-1.5rem))] md:w-[min(420px,calc(100vw-1.5rem))]",
                  "rounded-2xl border bg-card shadow-2xl",
                  "animate-in fade-in zoom-in-95 duration-200",
                  PANEL_POSITION_CLASS[copilotPosition]
                )
          )}
        >
          <div
            className={cn(
              "flex min-h-0 flex-1 flex-col overflow-hidden",
              docked ? "rounded-xl border bg-card shadow-sm" : "rounded-2xl"
            )}
          >
            <Copilot
              mode={copilotMode}
              onToggleMode={() => setCopilotMode(copilotMode === "dock" ? "float" : "dock")}
              onClose={() => setCopilotOpen(false)}
              sessionId={copilotSessionId}
              onNewChat={startNewChat}
            />
          </div>
        </aside>
      )}

      {/* Draggable Copilot launcher — drag to move, click to open */}
      {!copilotOpen && (
        <div
          className={cn(
            "fixed z-40 select-none",
            dragging
              ? "cursor-grabbing"
              : "cursor-grab transition-[left,top,transform] duration-200",
            !dragging && FAB_POSITION_CLASS[copilotPosition]
          )}
          style={
            dragPoint
              ? { left: dragPoint.x, top: dragPoint.y, transform: "translate(-50%, -50%)" }
              : undefined
          }
          onPointerDown={onPointerDown}
          onPointerMove={onPointerMove}
          onPointerUp={onPointerUp}
          onPointerCancel={onPointerUp}
          onClick={() => {
            if (dragRef.current.justDragged) {
              dragRef.current.justDragged = false;
              return;
            }
            setCopilotOpen(true);
          }}
        >
          <Button
            aria-label="باز کردن دستیار هوشمند"
            className="pointer-events-none h-12 gap-2 rounded-full px-5 shadow-lg"
          >
            <Sparkles className="h-4 w-4" />
            دستیار
          </Button>
        </div>
      )}
    </div>
  );
}

export function App() {
  return (
    <ThemeProvider>
      <AppShell />
    </ThemeProvider>
  );
}

export default App;
