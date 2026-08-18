import { useState } from "react";
import { Menu, Sparkles } from "lucide-react";

import { Button } from "@/components/ui/button";
import { ThemeProvider } from "@/components/theme-provider";
import { Sidebar, type View } from "@/components/sidebar";
import { Dashboard } from "@/components/dashboard";
import { Customers } from "@/components/customers";
import { Analyses } from "@/components/analyses";
import { Copilot, type CopilotMode } from "@/components/copilot";
import { AppBackground } from "@/components/app-background";

function AppShell() {
  const [view, setView] = useState<View>("dashboard");
  const [copilotOpen, setCopilotOpen] = useState(false);
  const [copilotMode, setCopilotMode] = useState<CopilotMode>("float");
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const docked = copilotOpen && copilotMode === "dock";

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
          aria-label="Open navigation"
          className="fixed left-2 top-2 z-40 rounded-full shadow-md md:hidden"
        >
          <Menu className="h-5 w-5" />
        </Button>
      )}

      {/* Copilot: full-screen docked card next to the sidebar */}
      {copilotOpen && copilotMode === "dock" && (
        <aside className="fixed inset-0 z-50 flex flex-col p-2 md:p-3 lg:static lg:z-auto lg:flex-1 lg:animate-none lg:p-0">
          <div className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-xl border shadow-sm">
            <Copilot
              mode="dock"
              onToggleMode={() => setCopilotMode("float")}
              onClose={() => setCopilotOpen(false)}
            />
          </div>
        </aside>
      )}

      {/* Copilot: floating window */}
      {copilotOpen && copilotMode === "float" && (
        <aside
          className="fixed bottom-2 right-2 z-50 flex flex-col overflow-hidden rounded-2xl border shadow-2xl h-[min(680px,calc(100vh-1rem))] w-[min(420px,calc(100vw-1rem))] md:bottom-3 md:right-3 md:h-[min(680px,calc(100vh-1.5rem))] md:w-[min(420px,calc(100vw-1.5rem))] animate-in fade-in zoom-in-95 duration-200"
          aria-label="AI Copilot"
        >
          <Copilot
            mode="float"
            onToggleMode={() => setCopilotMode("dock")}
            onClose={() => setCopilotOpen(false)}
          />
        </aside>
      )}

      {/* Floating action button to open the copilot */}
      {!copilotOpen && (
        <Button
          onClick={() => setCopilotOpen(true)}
          aria-label="Open Copilot"
          className="fixed bottom-2 right-2 z-40 h-12 gap-2 rounded-full px-5 shadow-lg md:bottom-3 md:right-3"
        >
          <Sparkles className="h-4 w-4" />
          Copilot
        </Button>
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
