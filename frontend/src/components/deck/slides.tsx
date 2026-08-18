import { type CSSProperties, type ReactNode } from "react";
import {
  AlertTriangle,
  ArrowRight,
  BadgeCheck,
  Building2,
  CheckCircle2,
  Clock,
  Database,
  Eye,
  FileText,
  Layers,
  Lightbulb,
  Link2,
  ListChecks,
  MessageSquareWarning,
  Network,
  Rocket,
  Search,
  ShieldAlert,
  ShoppingCart,
  Sparkles,
  Timer,
  TrendingDown,
  TrendingUp,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { getCustomer360 } from "@/lib/customer-intelligence";
import { COPILOT_SCENARIOS } from "@/lib/copilot-scenarios";
import { customers, riskColor } from "@/lib/mock-data";
import { formatCurrency, formatPercent } from "@/lib/utils";

/* ---------- shared deck primitives ---------- */

function SlideShell({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div
      className={cn(
        "flex min-h-full flex-col justify-center px-6 py-8 md:px-12 md:py-10",
        className
      )}
    >
      {children}
    </div>
  );
}

function Eyebrow({ children }: { children: ReactNode }) {
  return (
    <span className="inline-flex w-fit items-center gap-1.5 rounded-full border border-primary/30 bg-primary/10 px-3 py-1 text-[11px] font-semibold uppercase tracking-widest text-primary">
      <Sparkles className="h-3 w-3" />
      {children}
    </span>
  );
}

function SlideTitle({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <h2
      className={cn(
        "mt-4 font-display text-3xl font-bold tracking-tight md:text-5xl",
        className
      )}
    >
      {children}
    </h2>
  );
}

function SlideSub({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <p className={cn("mt-3 max-w-2xl text-base text-muted-foreground md:text-lg", className)}>
      {children}
    </p>
  );
}

function GlassCard({
  children,
  className,
  style,
}: {
  children: ReactNode;
  className?: string;
  style?: CSSProperties;
}) {
  return (
    <div
      className={cn(
        "rounded-2xl border bg-card/70 p-5 shadow-sm backdrop-blur",
        className
      )}
      style={style}
    >
      {children}
    </div>
  );
}

function stagger(i: number) {
  return { animationDelay: `${i * 90}ms` };
}

/* ---------- 1 · Cover ---------- */

function CoverSlide() {
  return (
    <SlideShell className="items-center text-center">
      <div className="animate-float">
        <span className="inline-flex items-center gap-2 rounded-full border border-primary/30 bg-primary/10 px-4 py-1.5 text-xs font-semibold uppercase tracking-[0.25em] text-primary">
          <Sparkles className="h-3.5 w-3.5" />
          Customer Intelligence Platform
        </span>
        <h1 className="mt-6 font-display text-6xl font-extrabold tracking-tight md:text-8xl">
          <span className="deck-gradient-text">CustIntel</span>
        </h1>
        <p className="mx-auto mt-6 max-w-2xl text-xl text-muted-foreground md:text-2xl">
          A complete 360° picture of every customer — in seconds, without manual searching.
        </p>
        <p className="mt-10 inline-flex items-center gap-2 rounded-full border bg-background/50 px-4 py-2 text-sm text-muted-foreground backdrop-blur">
          Press
          <kbd className="rounded-md border bg-muted px-1.5 py-0.5 font-mono text-xs">→</kbd>
          to present
        </p>
      </div>
    </SlideShell>
  );
}

/* ---------- 2 · Problem ---------- */

const problems = [
  {
    icon: Building2,
    title: "Data scattered everywhere",
    text: "CRM, sales, complaints, and reports live in disconnected systems.",
  },
  {
    icon: Search,
    title: "Manual searching",
    text: "Teams stitch together a customer picture record by record, by hand.",
  },
  {
    icon: AlertTriangle,
    title: "Risk is invisible",
    text: "Declining purchases and rising complaints surface too late to act.",
  },
  {
    icon: Clock,
    title: "Slow decisions",
    text: "By the time you have the full story, the opportunity is already gone.",
  },
];

function ProblemSlide() {
  return (
    <SlideShell>
      <Eyebrow>The problem</Eyebrow>
      <SlideTitle>Great customer intelligence shouldn't be this hard.</SlideTitle>
      <SlideSub>
        Customer data lives in many places. Without a single view, teams lose time, miss risks,
        and leave revenue on the table.
      </SlideSub>
      <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {problems.map((p, i) => {
          const Icon = p.icon;
          return (
            <GlassCard key={p.title} className="animate-fade-in-up" style={stagger(i)}>
              <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-red-500/10 text-red-500">
                <Icon className="h-5 w-5" />
              </span>
              <p className="mt-4 font-display text-base font-semibold">{p.title}</p>
              <p className="mt-1.5 text-sm text-muted-foreground">{p.text}</p>
            </GlassCard>
          );
        })}
      </div>
    </SlideShell>
  );
}

/* ---------- 3 · Solution / Customer 360 ---------- */

const sources = [
  { icon: Network, label: "CRM" },
  { icon: ShoppingCart, label: "Sales / Orders" },
  { icon: MessageSquareWarning, label: "Complaints" },
  { icon: FileText, label: "Reports" },
  { icon: Layers, label: "Product requests" },
];

function SolutionSlide() {
  return (
    <SlideShell>
      <Eyebrow>The solution</Eyebrow>
      <SlideTitle>One canonical Customer 360.</SlideTitle>
      <SlideSub>
        Link every source to a single Customer Master — each connection carrying a confidence
        score. No source-to-source guessing.
      </SlideSub>
      <div className="mt-10 grid items-center gap-8 lg:grid-cols-2">
        <GlassCard className="flex flex-col items-center gap-4 p-8">
          <span className="flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-indigo-500 to-fuchsia-500 text-white shadow-lg">
            <Database className="h-8 w-8" />
          </span>
          <p className="font-display text-lg font-semibold">Customer Master</p>
          <div className="w-full space-y-2">
            {sources.map((s) => {
              const Icon = s.icon;
              return (
                <div
                  key={s.label}
                  className="flex items-center justify-between rounded-xl border bg-background/60 px-4 py-2.5 text-sm"
                >
                  <span className="flex items-center gap-2">
                    <Icon className="h-4 w-4 text-primary" />
                    {s.label}
                  </span>
                  <span className="font-mono text-xs text-emerald-500">linked ✓</span>
                </div>
              );
            })}
          </div>
        </GlassCard>

        <div className="space-y-4">
          {[
            { title: "Complete in seconds", text: "Every signal about a customer in one place.", icon: Eye },
            { title: "Explainable confidence", text: "Know exactly how and why records matched.", icon: BadgeCheck },
            { title: "Ready for action", text: "Risk, complaints, and opportunities at a glance.", icon: Lightbulb },
          ].map((f, i) => {
            const Icon = f.icon;
            return (
              <GlassCard key={f.title} className="animate-fade-in-up flex items-start gap-4" style={stagger(i)}>
                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary">
                  <Icon className="h-5 w-5" />
                </span>
                <div>
                  <p className="font-display font-semibold">{f.title}</p>
                  <p className="mt-0.5 text-sm text-muted-foreground">{f.text}</p>
                </div>
              </GlassCard>
            );
          })}
        </div>
      </div>
    </SlideShell>
  );
}

/* ---------- 4 · How it works ---------- */

const pipeline = [
  { icon: Link2, title: "Exact matching", text: "IDs, email, phone, company identifier." },
  { icon: Search, title: "Candidate generation", text: "Cheap signals narrow to a few likely customers." },
  { icon: ListChecks, title: "Fuzzy & structured", text: "Names, companies, addresses, semantics." },
  { icon: Sparkles, title: "Confidence score", text: "Explainable score — and the option to say “uncertain”." },
  { icon: CheckCircle2, title: "Customer 360", text: "Every record resolves to one canonical customer." },
];

function HowItWorksSlide() {
  return (
    <SlideShell>
      <Eyebrow>How it works</Eyebrow>
      <SlideTitle>Entity resolution, staged — not magic.</SlideTitle>
      <SlideSub>
        Each source record is independently linked to the right canonical customer with a
        transparent confidence score.
      </SlideSub>
      <div className="mt-10 grid gap-4 md:grid-cols-5">
        {pipeline.map((s, i) => {
          const Icon = s.icon;
          const last = i === pipeline.length - 1;
          return (
            <div key={s.title} className="relative">
              <GlassCard className="animate-fade-in-up h-full" style={stagger(i)}>
                <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 to-fuchsia-500 text-white">
                  <Icon className="h-5 w-5" />
                </span>
                <p className="mt-4 font-display text-sm font-semibold">{s.title}</p>
                <p className="mt-1 text-xs text-muted-foreground">{s.text}</p>
              </GlassCard>
              {!last && (
                <ArrowRight className="absolute -right-3.5 top-1/2 hidden h-5 w-5 -translate-y-1/2 text-primary/50 md:block" />
              )}
            </div>
          );
        })}
      </div>
    </SlideShell>
  );
}

/* ---------- 5 · Product (live mock) ---------- */

function ProductSlide() {
  const customer = customers.find((c) => c.id === "c2") ?? customers[0];
  const view = getCustomer360(customer);
  const risk = riskColor[customer.risk];
  const positive = customer.purchaseChange >= 0;

  return (
    <SlideShell>
      <Eyebrow>Showing our product</Eyebrow>
      <SlideTitle>Every customer, one intelligent view.</SlideTitle>
      <SlideSub className="max-w-3xl">
        This is rendered live from the same data the platform uses — an explainable risk score,
        sales and complaint signals, and opportunities for {customer.name}.
      </SlideSub>

      <div className="mt-8 grid gap-4 md:grid-cols-3">
        <GlassCard className="animate-fade-in-up" style={stagger(0)}>
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            <ShieldAlert className="h-4 w-4 text-amber-500" />
            Risk score
          </div>
          <div className="mt-3 flex items-baseline gap-1">
            <span className="font-mono text-5xl font-semibold tabular-nums">{view.riskScore}</span>
            <span className="text-sm text-muted-foreground">/ 100</span>
          </div>
          <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-muted">
            <div
              className={cn("h-full rounded-full", risk.dot)}
              style={{ width: `${view.riskScore}%` }}
            />
          </div>
          <p className={cn("mt-2 text-sm font-medium", risk.text)}>{risk.label} risk</p>
          <div className="mt-4 space-y-2 border-t pt-3">
            {view.riskSignals.slice(0, 2).map((s) => (
              <p key={s.label} className="text-xs text-muted-foreground">
                • {s.label} — {s.detail}
              </p>
            ))}
          </div>
        </GlassCard>

        <GlassCard className="animate-fade-in-up" style={stagger(1)}>
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            <ShoppingCart className="h-4 w-4 text-primary" />
            Sales snapshot
          </div>
          <p className="mt-3 text-xs text-muted-foreground">Trailing revenue</p>
          <p className="font-mono text-3xl font-semibold tabular-nums">
            {formatCurrency(customer.revenue)}
          </p>
          <p
            className={cn(
              "mt-2 inline-flex items-center gap-1 text-sm font-medium",
              positive ? "text-emerald-500" : "text-red-500"
            )}
          >
            {positive ? <TrendingUp className="h-4 w-4" /> : <TrendingDown className="h-4 w-4" />}
            {formatPercent(customer.purchaseChange)} vs prior
          </p>
          <div className="mt-4 space-y-2 border-t pt-3 text-sm">
            <p className="flex justify-between">
              <span className="text-muted-foreground">Orders</span>
              <span className="font-mono tabular-nums">{view.orders}</span>
            </p>
            <p className="flex justify-between">
              <span className="text-muted-foreground">Top product</span>
              <span>{view.topProduct}</span>
            </p>
          </div>
        </GlassCard>

        <GlassCard className="animate-fade-in-up" style={stagger(2)}>
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            <MessageSquareWarning className="h-4 w-4 text-red-400" />
            Complaints &amp; opportunity
          </div>
          <div className="mt-3 flex gap-6">
            <div>
              <p className="font-mono text-3xl font-semibold tabular-nums">{customer.complaints}</p>
              <p className="text-xs text-muted-foreground">complaints</p>
            </div>
            <div>
              <p className="font-mono text-3xl font-semibold tabular-nums">
                {view.qualityComplaints}
              </p>
              <p className="text-xs text-muted-foreground">quality</p>
            </div>
          </div>
          <div className="mt-4 space-y-2 border-t pt-3">
            {view.opportunities.slice(0, 2).map((o) => (
              <div key={o.title} className="flex items-center justify-between text-sm">
                <span className="flex items-center gap-1.5 text-muted-foreground">
                  <Lightbulb className="h-3.5 w-3.5 text-amber-500" />
                  {o.title}
                </span>
                <span className="font-mono text-xs tabular-nums">{o.score}/100</span>
              </div>
            ))}
          </div>
        </GlassCard>
      </div>
    </SlideShell>
  );
}

/* ---------- 6 · Product UI (browser mock) ---------- */

function MiniBar({ height, label, value }: { height: string; label: string; value: string }) {
  return (
    <div className="flex flex-1 flex-col items-center gap-1.5">
      <div className="flex h-24 w-full items-end rounded-lg bg-muted/60">
        <div
          className="w-full rounded-md bg-gradient-to-t from-indigo-500 to-fuchsia-400"
          style={{ height }}
        />
      </div>
      <span className="text-xs text-muted-foreground">{label}</span>
      <span className="font-mono text-xs tabular-nums">{value}</span>
    </div>
  );
}

function ProductUISlide() {
  const kpis = [
    { label: "Total customers", value: "1,284" },
    { label: "At risk", value: "87", tone: "text-red-500" },
    { label: "Complaints", value: "124" },
    { label: "Revenue", value: "$5.2M", tone: "text-emerald-500" },
  ];
  return (
    <SlideShell>
      <Eyebrow>Product in action</Eyebrow>
      <SlideTitle>Designed for the people who own the customer.</SlideTitle>
      <div className="mx-auto mt-10 w-full max-w-4xl overflow-hidden rounded-2xl border bg-card shadow-2xl">
        {/* browser chrome */}
        <div className="flex items-center gap-2 border-b bg-muted/40 px-4 py-3">
          <span className="h-3 w-3 rounded-full bg-red-400" />
          <span className="h-3 w-3 rounded-full bg-amber-400" />
          <span className="h-3 w-3 rounded-full bg-emerald-400" />
          <div className="mx-auto rounded-md bg-background px-4 py-1 text-xs text-muted-foreground">
            app.custintel.ai
          </div>
        </div>
        {/* dashboard mock */}
        <div className="grid grid-cols-2 gap-3 p-4 sm:grid-cols-4">
          {kpis.map((k, i) => (
            <div
              key={k.label}
              className="animate-fade-in-up rounded-xl border bg-background/70 p-3"
              style={stagger(i)}
            >
              <p className="text-[11px] text-muted-foreground">{k.label}</p>
              <p className={cn("mt-1 font-mono text-xl font-semibold tabular-nums", k.tone)}>
                {k.value}
              </p>
            </div>
          ))}
        </div>
        <div className="grid grid-cols-2 gap-3 p-4 pt-0">
          <div className="rounded-xl border bg-background/70 p-4">
            <p className="mb-3 text-xs font-medium text-muted-foreground">Purchase trend</p>
            <div className="flex gap-2">
              <MiniBar height="55%" label="Jun" value="$4.0M" />
              <MiniBar height="68%" label="Jul" value="$4.3M" />
              <MiniBar height="82%" label="Aug" value="$4.6M" />
            </div>
          </div>
          <div className="rounded-xl border bg-background/70 p-4">
            <p className="mb-3 text-xs font-medium text-muted-foreground">Customer intelligence</p>
            <div className="space-y-2">
              {[
                { label: "High risk", w: "26%", tone: "bg-red-500" },
                { label: "Medium risk", w: "40%", tone: "bg-amber-500" },
                { label: "Low risk", w: "58%", tone: "bg-emerald-500" },
              ].map((r) => (
                <div key={r.label} className="flex items-center gap-2 text-xs">
                  <span className="w-24 shrink-0 text-muted-foreground">{r.label}</span>
                  <div className="h-2 flex-1 overflow-hidden rounded-full bg-muted">
                    <div className={cn("h-full rounded-full", r.tone)} style={{ width: r.w }} />
                  </div>
                </div>
              ))}
            </div>
            <p className="mt-4 text-xs text-muted-foreground">
              Each card explains <span className="text-foreground">why</span> — no black boxes.
            </p>
          </div>
        </div>
      </div>
    </SlideShell>
  );
}

/* ---------- 7 · Value ---------- */

const values = [
  { icon: Timer, stat: "Seconds", label: "to a complete customer picture", accent: "text-indigo-500" },
  { icon: Eye, stat: "360°", label: "every signal, in one view", accent: "text-fuchsia-500" },
  { icon: BadgeCheck, stat: "Explainable", label: "confidence on every match", accent: "text-emerald-500" },
  { icon: TrendingUp, stat: "+", label: "retention & upsell revenue", accent: "text-amber-500" },
];

function ValueSlide() {
  return (
    <SlideShell>
      <Eyebrow>Why it matters</Eyebrow>
      <SlideTitle>Clarity for managers, action for teams.</SlideTitle>
      <SlideSub>
        Stop searching. Start understanding — with explainable answers your leadership can act on.
      </SlideSub>
      <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {values.map((v, i) => {
          const Icon = v.icon;
          return (
            <GlassCard key={v.label} className="animate-fade-in-up" style={stagger(i)}>
              <span className={cn("flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10", v.accent)}>
                <Icon className="h-5 w-5" />
              </span>
              <p className={cn("mt-4 font-display text-3xl font-bold tracking-tight", v.accent)}>
                {v.stat}
              </p>
              <p className="mt-1 text-sm text-muted-foreground">{v.label}</p>
            </GlassCard>
          );
        })}
      </div>
    </SlideShell>
  );
}

/* ---------- 8 · Roadmap ---------- */

const roadmap = [
  { phase: "Now", icon: Rocket, text: "Customer 360, explainable risk, complaint↔purchase, upsell & cross-sell.", current: true },
  { phase: "Next", icon: Sparkles, text: "Predictive churn & revenue models, semantic search for the Copilot.", current: false },
  { phase: "Later", icon: Network, text: "Cross-org intelligence and proactive opportunity alerts.", current: false },
];

function RoadmapSlide() {
  return (
    <SlideShell>
      <Eyebrow>Roadmap</Eyebrow>
      <SlideTitle>Start simple. Grow with the data.</SlideTitle>
      <SlideSub>
        A transparent MVP first — advanced models only when the dataset earns them.
      </SlideSub>
      <div className="mt-10 grid gap-4 md:grid-cols-3">
        {roadmap.map((r, i) => {
          const Icon = r.icon;
          return (
            <GlassCard
              key={r.phase}
              className={cn(
                "animate-fade-in-up",
                r.current && "border-primary/50 bg-primary/[0.07]"
              )}
              style={stagger(i)}
            >
              <div className="flex items-center gap-2">
                <span
                  className={cn(
                    "flex h-9 w-9 items-center justify-center rounded-xl",
                    r.current
                      ? "bg-gradient-to-br from-indigo-500 to-fuchsia-500 text-white"
                      : "bg-muted text-muted-foreground"
                  )}
                >
                  <Icon className="h-4 w-4" />
                </span>
                <span className="font-display text-sm font-semibold">{r.phase}</span>
                {r.current && (
                  <span className="ml-auto rounded-full bg-emerald-500/15 px-2 py-0.5 text-[10px] font-semibold uppercase text-emerald-500">
                    MVP
                  </span>
                )}
              </div>
              <p className="mt-3 text-sm text-muted-foreground">{r.text}</p>
            </GlassCard>
          );
        })}
      </div>
    </SlideShell>
  );
}

/* ---------- 9 · Closing ---------- */

function ClosingSlide() {
  return (
    <SlideShell className="items-center text-center">
      <div className="animate-float">
        <span className="inline-flex items-center gap-2 rounded-full border border-primary/30 bg-primary/10 px-4 py-1.5 text-xs font-semibold uppercase tracking-[0.25em] text-primary">
          <Sparkles className="h-3.5 w-3.5" />
          Let's talk
        </span>
        <h2 className="mt-6 font-display text-5xl font-extrabold tracking-tight md:text-7xl">
          Give your team a <span className="deck-gradient-text">complete picture</span> of every
          customer.
        </h2>
        <p className="mx-auto mt-5 max-w-2xl text-lg text-muted-foreground">
          CustIntel connects your customer data and turns it into clear, actionable intelligence —
          in seconds.
        </p>
        <div className="mt-9 flex flex-wrap items-center justify-center gap-3">
          <Button size="lg" className="h-12 gap-2 rounded-full px-6">
            Request a demo
            <ArrowRight className="h-4 w-4" />
          </Button>
          <Button size="lg" variant="outline" className="h-12 rounded-full px-6">
            hello@custintel.ai
          </Button>
        </div>
      </div>
    </SlideShell>
  );
}

/* ---------- 7.5 · Copilot scenarios ---------- */

const scenarioChat = [
  {
    role: "user",
    text: "Which high-value customers are at risk?",
  },
  {
    role: "agent",
    text: "I found 5 high-risk accounts representing $1.2M in revenue, with declining purchases and elevated complaints.",
    chips: ["5 at risk", "-18.2% avg", "$1.2M rev"],
  },
  {
    role: "user",
    text: "What are the main complaint reasons?",
  },
  {
    role: "agent",
    text: "Billing errors lead the list (96), followed by delivery delays (74) and product quality (61).",
    chips: ["Top: Billing", "3 reasons", "+4.8%"],
  },
] as const;

function CopilotScenariosSlide() {
  return (
    <SlideShell>
      <Eyebrow>Meet your Copilot</Eyebrow>
      <SlideTitle>Ask in plain language. Get answers in seconds.</SlideTitle>
      <SlideSub>
        Managers ask natural questions — the Copilot answers with structured insights, no manual
        digging.
      </SlideSub>

      <div className="mt-8 grid items-start gap-4 lg:grid-cols-2">
        {/* chat mock */}
        <GlassCard className="space-y-3 p-4">
          {scenarioChat.map((m) =>
            m.role === "user" ? (
              <div key={m.text} className="flex justify-end">
                <div className="max-w-[85%] rounded-2xl rounded-tr-sm bg-primary px-3.5 py-2 text-sm text-primary-foreground">
                  {m.text}
                </div>
              </div>
            ) : (
              <div key={m.text} className="flex justify-start">
                <div className="max-w-[92%]">
                  <div className="rounded-2xl rounded-tl-sm bg-muted px-3.5 py-2 text-sm">
                    {m.text}
                  </div>
                  <div className="mt-1.5 flex flex-wrap gap-1.5">
                    {m.chips.map((c) => (
                      <span
                        key={c}
                        className="rounded-full border bg-background px-2 py-0.5 text-[11px] text-muted-foreground"
                      >
                        {c}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            )
          )}
        </GlassCard>

        {/* scenario cards */}
        <div className="flex flex-col gap-3">
          {COPILOT_SCENARIOS.map((s, i) => {
            const Icon = s.icon;
            return (
              <GlassCard
                key={s.id}
                className="animate-fade-in-up flex items-start gap-4"
                style={stagger(i)}
              >
                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary">
                  <Icon className="h-5 w-5" />
                </span>
                <div>
                  <p className="font-display font-semibold">{s.title}</p>
                  <p className="mt-0.5 text-sm text-muted-foreground">{s.description}</p>
                </div>
              </GlassCard>
            );
          })}
        </div>
      </div>
    </SlideShell>
  );
}

/* ---------- deck export ---------- */

export interface DeckSlide {
  id: string;
  label: string;
  render: () => ReactNode;
}

export const PITCH_SLIDES: DeckSlide[] = [
  { id: "cover", label: "Cover", render: () => <CoverSlide /> },
  { id: "problem", label: "Problem", render: () => <ProblemSlide /> },
  { id: "solution", label: "Solution", render: () => <SolutionSlide /> },
  { id: "how", label: "How it works", render: () => <HowItWorksSlide /> },
  { id: "product", label: "Product", render: () => <ProductSlide /> },
  { id: "ui", label: "Product UI", render: () => <ProductUISlide /> },
  { id: "copilot", label: "Copilot scenarios", render: () => <CopilotScenariosSlide /> },
  { id: "value", label: "Value", render: () => <ValueSlide /> },
  { id: "roadmap", label: "Roadmap", render: () => <RoadmapSlide /> },
  { id: "closing", label: "Ask", render: () => <ClosingSlide /> },
];
