import { type CSSProperties, type ReactNode } from "react";
import {
  AlertTriangle,
  ArrowLeft,
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
  Sparkles,
  Timer,
  TrendingUp,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

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
          پلتفرم هوشمند مشتری
        </span>
        <h1 className="mt-6 font-display text-6xl font-extrabold tracking-tight md:text-8xl">
          <span className="deck-gradient-text">بینش مشتری</span>
        </h1>
        <p className="mx-auto mt-6 max-w-2xl text-xl text-muted-foreground md:text-2xl">
          تصویر کامل ۳۶۰ درجه از هر مشتری — در چند ثانیه، بدون جستجوی دستی.
        </p>
        <p className="mt-10 inline-flex items-center gap-2 rounded-full border bg-background/50 px-4 py-2 text-sm text-muted-foreground backdrop-blur">
          برای نمایش، کلید
          <kbd className="rounded-md border bg-muted px-1.5 py-0.5 font-mono text-xs">→</kbd>
          را بزنید
        </p>
      </div>
    </SlideShell>
  );
}

/* ---------- 2 · Problem ---------- */

const problems = [
  {
    icon: Building2,
    title: "پراکندگی داده‌ها",
    text: "CRM، فروش، شکایات و گزارش‌ها در سیستم‌های جدا از هم زندگی می‌کنند.",
  },
  {
    icon: Search,
    title: "جستجوی دستی",
    text: "تیم‌ها تصویر مشتری را رکورد به رکورد و با دست کنار هم می‌چینند.",
  },
  {
    icon: AlertTriangle,
    title: "ریسک نامرئی",
    text: "کاهش خرید و افزایش شکایات خیلی دیر دیده می‌شوند تا بتوان اقدامی کرد.",
  },
  {
    icon: Clock,
    title: "تصمیم‌های کند",
    text: "تا وقتی تصویر کامل را دارید، فرصت از دست رفته است.",
  },
];

function ProblemSlide() {
  return (
    <SlideShell>
      <Eyebrow>مسئله</Eyebrow>
      <SlideTitle>هوش مشتری خوب نباید این‌قدر سخت باشد.</SlideTitle>
      <SlideSub>
        داده‌های مشتریان در جاهای زیادی پراکنده‌اند. بدون یک نمای واحد، تیم‌ها زمان را از دست
        می‌دهند، ریسک‌ها را از دست می‌دهند و درآمد را روی میز جا می‌گذارند.
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
  { icon: FileText, label: "فروش / سفارش" },
  { icon: MessageSquareWarning, label: "شکایات" },
  { icon: Layers, label: "گزارش‌ها" },
  { icon: Sparkles, label: "درخواست محصول" },
];

function SolutionSlide() {
  return (
    <SlideShell>
      <Eyebrow>راه‌حل</Eyebrow>
      <SlideTitle>یک نمای واحد ۳۶۰ درجه از مشتری.</SlideTitle>
      <SlideSub>
        هر منبع را به یک استاد مشتری واحد متصل کن — هر اتصال با نمره اطمینان. بدون حدس بین
        منبع‌ها.
      </SlideSub>
      <div className="mt-10 grid items-center gap-8 lg:grid-cols-2">
        <GlassCard className="flex flex-col items-center gap-4 p-8">
          <span className="flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-indigo-500 to-fuchsia-500 text-white shadow-lg">
            <Database className="h-8 w-8" />
          </span>
          <p className="font-display text-lg font-semibold">استاد مشتری</p>
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
                  <span className="font-mono text-xs text-emerald-500">متصل ✓</span>
                </div>
              );
            })}
          </div>
        </GlassCard>

        <div className="space-y-4">
          {[
            { title: "تکمیل در چند ثانیه", text: "هر سیگنال درباره مشتری در یک جا.", icon: Eye },
            { title: "اطمینان قابل توضیح", text: "دقیقاً بدانید رکوردها چگونه و چرا تطبیق یافتند.", icon: BadgeCheck },
            { title: "آماده اقدام", text: "ریسک، شکایات و فرصت‌ها در یک نگاه.", icon: Lightbulb },
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
  { icon: Link2, title: "تطبیق دقیق", text: "شناسه، ایمیل، تلفن، شناسه شرکت." },
  { icon: Search, title: "تولید نامزد", text: "سیگنال‌های کم‌هزینه به چند مشتری محتمل محدود می‌کنند." },
  { icon: ListChecks, title: "فازی و ساخت‌یافته", text: "نام‌ها، شرکت‌ها، آدرس‌ها، معناشناسی." },
  { icon: Sparkles, title: "نمره اطمینان", text: "نمره قابل توضیح — و امکان گفتن «نامطمئن»." },
  { icon: CheckCircle2, title: "نمای ۳۶۰ مشتری", text: "هر رکورد به یک مشتری واحد و معیار می‌رسد." },
];

function HowItWorksSlide() {
  return (
    <SlideShell>
      <Eyebrow>روش کار</Eyebrow>
      <SlideTitle>تفکیک موجودیت، مرحله‌ای — نه جادو.</SlideTitle>
      <SlideSub>
        هر رکورد منبع به‌طور مستقل به استاد مشتری درست با نمره اطمینان شفاف متصل می‌شود.
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
                <ArrowLeft className="absolute -left-3.5 top-1/2 hidden h-5 w-5 -translate-y-1/2 text-primary/50 md:block" />
              )}
            </div>
          );
        })}
      </div>
    </SlideShell>
  );
}

/* ---------- 5 · Value ---------- */

const values = [
  { icon: Timer, stat: "ثانیه", label: "تا تصویر کامل مشتری", accent: "text-indigo-500" },
  { icon: Eye, stat: "۳۶۰°", label: "همه سیگنال‌ها در یک نگاه", accent: "text-fuchsia-500" },
  { icon: BadgeCheck, stat: "قابل توضیح", label: "اطمینان بر هر تطبیق", accent: "text-emerald-500" },
  { icon: TrendingUp, stat: "+", label: "درآمد حفظ و فروش بیشتر", accent: "text-amber-500" },
];

function ValueSlide() {
  return (
    <SlideShell>
      <Eyebrow>چرا اهمیت دارد</Eyebrow>
      <SlideTitle>شفافیت برای مدیران، اقدام برای تیم‌ها.</SlideTitle>
      <SlideSub>
        جستجو را متوقف کن. درک کن — با پاسخ‌های قابل توضیح که مدیران می‌توانند بر آن‌ها اقدام
        کنند.
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

/* ---------- 6 · Roadmap ---------- */

const roadmap = [
  { phase: "اکنون", icon: Rocket, text: "نمای ۳۶۰ مشتری، ریسک قابل توضیح، شکایت↔خرید، افزایش و فروش متقابل.", current: true },
  { phase: "بعدی", icon: Sparkles, text: "مدل‌های پیش‌بینی ریزش و درآمد، جستجوی معنایی برای دستیار.", current: false },
  { phase: "بعداً", icon: Network, text: "هوش بین‌سازمانی و هشدارهای فرصت فعال.", current: false },
];

function RoadmapSlide() {
  return (
    <SlideShell>
      <Eyebrow>نقشه راه</Eyebrow>
      <SlideTitle>ساده شروع کن. با داده بزرگ شو.</SlideTitle>
      <SlideSub>
        ابتدا یک MVP شفاف — مدل‌های پیشرفته فقط وقتی داده آن‌ها را شایسته کند.
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
                  <span className="mr-auto rounded-full bg-emerald-500/15 px-2 py-0.5 text-[10px] font-semibold uppercase text-emerald-500">
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

/* ---------- 7 · Closing ---------- */

function ClosingSlide() {
  return (
    <SlideShell className="items-center text-center">
      <div className="animate-float">
        <span className="inline-flex items-center gap-2 rounded-full border border-primary/30 bg-primary/10 px-4 py-1.5 text-xs font-semibold uppercase tracking-[0.25em] text-primary">
          <Sparkles className="h-3.5 w-3.5" />
          گفت‌وگو
        </span>
        <h2 className="mt-6 font-display text-5xl font-extrabold tracking-tight md:text-7xl">
          به تیم‌تان یک <span className="deck-gradient-text">تصویر کامل</span> از هر مشتری
          بدهید.
        </h2>
        <p className="mx-auto mt-5 max-w-2xl text-lg text-muted-foreground">
          بینش مشتری داده‌های شما را به هم متصل می‌کند و به هوش واضح و عملی تبدیل می‌کند — در
          چند ثانیه.
        </p>
        <div className="mt-9 flex flex-wrap items-center justify-center gap-3">
          <Button size="lg" className="h-12 gap-2 rounded-full px-6">
            درخواست دمو
          </Button>
          <Button size="lg" variant="outline" className="h-12 rounded-full px-6">
            hello@custintel.ai
          </Button>
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
  { id: "cover", label: "جلد", render: () => <CoverSlide /> },
  { id: "problem", label: "مسئله", render: () => <ProblemSlide /> },
  { id: "solution", label: "راه‌حل", render: () => <SolutionSlide /> },
  { id: "how", label: "روش کار", render: () => <HowItWorksSlide /> },
  { id: "value", label: "ارزش", render: () => <ValueSlide /> },
  { id: "roadmap", label: "نقشه راه", render: () => <RoadmapSlide /> },
  { id: "closing", label: "گفت‌وگو", render: () => <ClosingSlide /> },
];
