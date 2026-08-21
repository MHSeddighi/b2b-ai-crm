import { type CSSProperties, type ReactNode } from "react";
import {
  Activity,
  AlertTriangle,
  ArrowLeft,
  BadgeCheck,
  Eye,
  Lightbulb,
  MessageSquareWarning,
  Rocket,
  ShieldAlert,
  ShoppingCart,
  Sparkles,
  Target,
  TrendingDown,
  TrendingUp,
} from "lucide-react";
import {
  Area,
  AreaChart,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  CartesianGrid,
} from "recharts";

import { Badge } from "@/components/ui/badge";
import { PITCH } from "@/lib/pitch-data";
import { formatCompact, formatNumber, withDot, cn } from "@/lib/utils";

/* ------------------------------------------------------------------ deck
   Shared primitives — same design language as the rest of the product. */

function SlideShell({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div
      className={cn(
        "flex min-h-full flex-col justify-center px-6 py-6 md:px-12 md:py-8",
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
        "mt-3 font-display text-2xl font-bold tracking-tight md:text-4xl",
        className
      )}
    >
      {children}
    </h2>
  );
}

function SlideSub({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <p className={cn("mt-2 max-w-3xl text-sm text-muted-foreground md:text-base", className)}>
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
        "rounded-2xl border bg-card/70 p-4 shadow-sm backdrop-blur",
        className
      )}
      style={style}
    >
      {children}
    </div>
  );
}

function stagger(i: number) {
  return { animationDelay: `${i * 70}ms` };
}

/** Big number with Persian digits. */
function BigStat({
  value,
  label,
  sub,
  accent = "text-primary",
}: {
  value: string;
  label: string;
  sub?: string;
  accent?: string;
}) {
  return (
    <GlassCard className="animate-fade-in-up">
      <p className={cn("font-display text-3xl font-extrabold tracking-tight tabular-nums md:text-4xl", accent)}>
        {value}
      </p>
      <p className="mt-1 text-sm font-semibold">{label}</p>
      {sub && <p className="mt-0.5 text-xs text-muted-foreground">{sub}</p>}
    </GlassCard>
  );
}

function RealDataNote() {
  return (
    <p className="mt-4 flex items-center gap-1.5 text-[11px] text-muted-foreground/80">
      <BadgeCheck className="h-3.5 w-3.5 text-emerald-500" />
      همه اعداد از داده واقعی سامانه و خروجی‌های از پیش محاسبه‌شده‌اند.
    </p>
  );
}

const pieColors = ["#6366f1", "#8b5cf6", "#10b981", "#f59e0b", "#ef4444", "#06b6d4"];

/* ============================================================ 1 · Cover */

function CoverSlide() {
  return (
    <SlideShell className="items-center text-center">
      <div className="animate-float">
        <span className="inline-flex items-center gap-2 rounded-full border border-primary/30 bg-primary/10 px-4 py-1.5 text-xs font-semibold uppercase tracking-[0.25em] text-primary">
          <Sparkles className="h-3.5 w-3.5" />
          {PITCH.productName}
        </span>
        <h1 className="mt-5 font-display text-5xl font-extrabold tracking-tight md:text-7xl">
          <span className="deck-gradient-text">بینش مشتری</span>
        </h1>
        <p className="mx-auto mt-4 max-w-2xl text-lg text-muted-foreground md:text-xl">
          سیگنال، ریسک و فرصت — و اقدام بعدی برای هر مشتری.
          <br className="hidden md:block" />
          همه از داده واقعی سامانه.
        </p>
        <p className="mt-8 inline-flex items-center gap-2 rounded-full border bg-background/50 px-4 py-2 text-sm text-muted-foreground backdrop-blur">
          برای شروع، کلید
          <kbd className="rounded-md border bg-muted px-1.5 py-0.5 font-mono text-xs">→</kbd>
          را بزنید
        </p>
      </div>
    </SlideShell>
  );
}

/* ====================================================== 2 · The problem */

function ProblemSlide() {
  return (
    <SlideShell>
      <Eyebrow>مسئله</Eyebrow>
      <SlideTitle>
        شرکت‌ها داده مشتری کم ندارند؛ <span className="text-primary">تصمیم به‌موقع</span> کم دارند.
      </SlideTitle>
      <SlideSub>
        {withDot("داده‌ها در ۱۶ منبع جدا از هم زندگی می‌کنند — فروش، شکایت، وصول، تعاملات، پیشنهادها — و هیچ‌کس نمی‌تواند آن‌ها را کنار هم بگذارد")}
      </SlideSub>

      <div className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {PITCH.gap.sources.map((s, i) => (
          <GlassCard key={s.title} className="animate-fade-in-up text-center" style={stagger(i)}>
            <p className="font-display text-2xl font-extrabold tabular-nums text-primary">{s.stat}</p>
            <p className="mt-1 text-sm font-semibold">{s.title}</p>
            <p className="mt-0.5 text-xs text-muted-foreground">{s.text}</p>
          </GlassCard>
        ))}
      </div>

      <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {PITCH.gap.pain.map((p, i) => (
          <GlassCard key={p.title} className="animate-fade-in-up" style={stagger(i)}>
            <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-red-500/10 text-red-500">
              <AlertTriangle className="h-4.5 w-4.5" />
            </span>
            <p className="mt-3 font-display text-sm font-semibold">{p.title}</p>
            <p className="mt-1 text-xs text-muted-foreground">{p.text}</p>
          </GlassCard>
        ))}
      </div>
      <RealDataNote />
    </SlideShell>
  );
}

/* ====================================================== 3 · The insight */

function InsightSlide() {
  const steps = PITCH.pipeline;
  return (
    <SlideShell>
      <Eyebrow>ایده اصلی</Eyebrow>
      <SlideTitle>از داده پراکنده تا اقدام بعدی — در پنج گام.</SlideTitle>
      <SlideSub>{withDot(PITCH.pipelineIdea)}</SlideSub>

      <div className="mt-8 grid gap-3 md:grid-cols-5">
        {steps.map((s, i) => {
          const last = i === steps.length - 1;
          return (
            <div key={s.title} className="relative">
              <GlassCard
                className={cn(
                  "animate-fade-in-up h-full text-center",
                  i === 2 && "border-primary/50 bg-primary/[0.06]"
                )}
                style={stagger(i)}
              >
                <span
                  className={cn(
                    "mx-auto flex h-9 w-9 items-center justify-center rounded-xl font-display text-sm font-bold",
                    i === 2
                      ? "bg-gradient-to-br from-indigo-500 to-fuchsia-500 text-white"
                      : "bg-primary/10 text-primary"
                  )}
                >
                  {i + 1}
                </span>
                <p className="mt-3 font-display text-sm font-semibold">{s.title}</p>
                <p className="mt-1 text-[11px] leading-relaxed text-muted-foreground">{s.text}</p>
              </GlassCard>
              {!last && (
                <ArrowLeft className="absolute -left-3.5 top-1/2 hidden h-5 w-5 -translate-y-1/2 text-primary/50 md:block" />
              )}
            </div>
          );
        })}
      </div>

      <GlassCard className="mt-6 flex items-center gap-3 border-primary/30 bg-primary/[0.05]">
        <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary">
          <Lightbulb className="h-5 w-5" />
        </span>
        <p className="text-sm leading-relaxed md:text-base">
          ما داده را فقط <span className="font-semibold">خلاصه</span> نمی‌کنیم؛ آن را به{" "}
          <span className="font-semibold text-primary">سیگنال‌های قابل اندازه‌گیری</span> و{" "}
          <span className="font-semibold text-primary">تصمیم‌های قابل اقدام</span> تبدیل می‌کنیم.
        </p>
      </GlassCard>
    </SlideShell>
  );
}

/* ========================================================= 4 · Product */

function ProductSlide() {
  const f = PITCH.featured;
  return (
    <SlideShell>
      <Eyebrow>محصول</Eyebrow>
      <SlideTitle>مشتری ۳۶۰ · سیگنال‌های هوشمند · اقدام بعدی.</SlideTitle>
      <SlideSub>
        {withDot("نمای واقعی محصول — کارت مشتری ۳۶۰ با داده واقعی مشتری «C_535756»")}
      </SlideSub>

      <div className="mt-6 grid gap-5 lg:grid-cols-5">
        {/* Real 360 card mock */}
        <div className="lg:col-span-3">
          <div className="animate-fade-in-up overflow-hidden rounded-2xl border bg-card shadow-sm">
            {/* window bar */}
            <div className="flex items-center gap-2 border-b bg-muted/40 px-4 py-2">
              <span className="h-2.5 w-2.5 rounded-full bg-red-400" />
              <span className="h-2.5 w-2.5 rounded-full bg-amber-400" />
              <span className="h-2.5 w-2.5 rounded-full bg-emerald-400" />
              <span className="mr-2 flex items-center gap-1.5 rounded-md bg-background px-2 py-0.5 font-mono text-[10px] text-muted-foreground">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                سامانه بینش مشتری · نمای ۳۶۰ درجه
              </span>
            </div>
            <div className="p-4">
              {/* header */}
              <div className="flex flex-wrap items-center gap-2">
                <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 to-violet-500 text-sm font-bold text-white">
                  {f.id.replace(/^C_/, "").slice(0, 2)}
                </span>
                <div className="leading-tight">
                  <p className="text-sm font-semibold tabular-nums">{f.id}</p>
                  <p className="text-[10px] text-muted-foreground">مشخصات مشتری</p>
                </div>
                <Badge variant="outline" className="mr-auto gap-1.5 border-transparent bg-amber-500/10 text-amber-600 dark:text-amber-400">
                  <span className="h-1.5 w-1.5 rounded-full bg-amber-500" />
                  ریسک {f.riskLevel} · {f.riskScore}
                </Badge>
              </div>
              {/* metrics */}
              <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-4">
                {[
                  { label: "درآمد کل", value: formatCompact(f.revenue) },
                  { label: "سفارش‌ها", value: formatNumber(f.orders) },
                  { label: "میانگین هر سفارش", value: formatCompact(f.avgOrderValue) },
                  { label: "شکایات", value: `${formatNumber(f.complaints)} (${formatNumber(f.openComplaints)} باز)` },
                ].map((m) => (
                  <div key={m.label} className="rounded-lg border bg-muted/30 px-2.5 py-2">
                    <p className="text-[10px] text-muted-foreground">{m.label}</p>
                    <p className="mt-0.5 truncate text-sm font-semibold tabular-nums">{m.value}</p>
                  </div>
                ))}
              </div>
              {/* state chips */}
              <div className="mt-2.5 flex flex-wrap gap-1.5">
                {f.state.map((s) => (
                  <span
                    key={s.key}
                    className={cn(
                      "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px]",
                      s.status === "بالا" || s.status === "سالم"
                        ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
                        : s.status === "ضعیف"
                          ? "bg-red-500/10 text-red-600 dark:text-red-400"
                          : "bg-amber-500/10 text-amber-600 dark:text-amber-400"
                    )}
                  >
                    <span
                      className={cn(
                        "h-1.5 w-1.5 rounded-full",
                        s.status === "بالا" || s.status === "سالم"
                          ? "bg-emerald-500"
                          : s.status === "ضعیف"
                            ? "bg-red-500"
                            : "bg-amber-500"
                      )}
                    />
                    {s.label}: {s.status}
                  </span>
                ))}
              </div>
              {/* signals */}
              <div className="mt-3 space-y-1.5 border-t pt-2.5">
                {f.signals.slice(0, 3).map((s) => (
                  <div key={s.label} className="flex items-start gap-2">
                    <span
                      className={cn(
                        "mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full",
                        s.tone === "negative" ? "bg-red-500" : s.tone === "positive" ? "bg-emerald-500" : "bg-amber-500"
                      )}
                    />
                    <div className="min-w-0 leading-tight">
                      <p className="text-[11px] font-medium">{s.label}</p>
                      <p className="text-[11px] text-muted-foreground">{s.reasons[0]}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* capabilities */}
        <div className="flex flex-col justify-center gap-3 lg:col-span-2">
          {[
            {
              icon: Eye,
              title: "مشتری ۳۶۰",
              text: "یک نمای واحد از فروش، شکایت، پرداخت، تعامل و فرصت.",
              accent: "text-indigo-500 bg-indigo-500/10",
            },
            {
              icon: Activity,
              title: "سیگنال‌های هوشمند",
              text: "چرخه خرید، اثر شکایت، رفتار پرداخت، سهم از سبد، سود واقعی، ریسک ریزش.",
              accent: "text-violet-500 bg-violet-500/10",
            },
            {
              icon: Target,
              title: "ریسک و فرصت",
              text: "ریزش، کاهش خرید، بدتر شدن پرداخت — و فروش متقابل، رشد درآمد، وفاداری.",
              accent: "text-amber-500 bg-amber-500/10",
            },
            {
              icon: Rocket,
              title: "اقدام بعدی",
              text: "سیستم می‌گوید با کدام مشتری، چرا، و چه‌کاری باید کرد.",
              accent: "text-emerald-500 bg-emerald-500/10",
            },
          ].map((c, i) => {
            const Icon = c.icon;
            return (
              <GlassCard key={c.title} className="animate-fade-in-up flex items-start gap-3" style={stagger(i)}>
                <span className={cn("flex h-9 w-9 shrink-0 items-center justify-center rounded-xl", c.accent)}>
                  <Icon className="h-4.5 w-4.5" />
                </span>
                <div>
                  <p className="font-display text-sm font-semibold">{c.title}</p>
                  <p className="mt-0.5 text-xs leading-relaxed text-muted-foreground">{c.text}</p>
                </div>
              </GlassCard>
            );
          })}
        </div>
      </div>
    </SlideShell>
  );
}

/* ==================================================== 5 · Real customer */

function CustomerStorySlide() {
  const f = PITCH.featured;
  return (
    <SlideShell className="py-4 md:py-5">
      <Eyebrow>مشتری واقعی</Eyebrow>
      <SlideTitle>
        درآمد بالا ≠ مشتری سالم.
      </SlideTitle>
      <SlideSub>{withDot(f.story)}</SlideSub>

      <div className="mt-4 grid gap-3 lg:grid-cols-2">
        {/* left — the "looks great" profile */}
        <GlassCard className="animate-fade-in-up">
          <div className="flex items-center gap-2">
            <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 to-violet-500 text-sm font-bold text-white">
              {f.id.replace(/^C_/, "").slice(0, 2)}
            </span>
            <div className="leading-tight">
              <p className="text-sm font-semibold tabular-nums">{f.id}</p>
              <p className="text-[11px] text-muted-foreground">بخش {f.segment} · {f.status}</p>
            </div>
            <Badge variant="outline" className="mr-auto gap-1.5 border-transparent bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
              نگاه اول: ارزشمند
            </Badge>
          </div>
          <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-4">
            <div className="rounded-xl border bg-muted/30 p-2 text-center">
              <p className="font-display text-lg font-extrabold tabular-nums text-emerald-600 dark:text-emerald-400">{formatCompact(f.revenue)}</p>
              <p className="mt-0.5 text-[10px] text-muted-foreground">درآمد کل</p>
            </div>
            <div className="rounded-xl border bg-muted/30 p-2 text-center">
              <p className="font-display text-lg font-extrabold tabular-nums">{formatNumber(f.orders)}</p>
              <p className="mt-0.5 text-[10px] text-muted-foreground">سفارش</p>
            </div>
            <div className="rounded-xl border bg-muted/30 p-2 text-center">
              <p className="font-display text-lg font-extrabold tabular-nums">{formatCompact(f.avgOrderValue)}</p>
              <p className="mt-0.5 text-[10px] text-muted-foreground">میانگین هر سفارش</p>
            </div>
            <div className="rounded-xl border bg-muted/30 p-2 text-center">
              <p className="font-display text-lg font-extrabold tabular-nums">۷ روز</p>
              <p className="mt-0.5 text-[10px] text-muted-foreground">چرخه عادی خرید</p>
            </div>
          </div>
          <div className="mt-2.5 space-y-1.5 text-xs">
            {[
              ["پس از شکایت، خرید", "۶۸٪ کاهش یافته"],
              ["از آخرین خرید گذشته", "۱٬۵۷۰ روز"],
              ["پرداخت با تأخیر", f.latePaymentsText],
              ["بدهی عقب‌افتاده", formatCompact(f.overdue)],
            ].map(([k, v]) => (
              <div key={k} className="flex items-center justify-between rounded-lg border bg-muted/30 px-2.5 py-1">
                <span className="text-muted-foreground">{k}</span>
                <span className="font-semibold tabular-nums text-red-600 dark:text-red-400">{v}</span>
              </div>
            ))}
          </div>
        </GlassCard>

        {/* right — what the signals say */}
        <div className="space-y-3">
          <GlassCard className="border-amber-500/30 bg-amber-500/[0.06]">
            <p className="text-xs font-semibold text-amber-600 dark:text-amber-400">وقتی سیگنال‌ها را کنار هم می‌گذاریم…</p>
            <div className="mt-2 space-y-1.5">
              {f.signals.slice(0, 3).map((s) => (
                <div key={s.label} className="flex items-start gap-2">
                  <span
                    className={cn(
                      "mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full",
                      s.tone === "negative" ? "bg-red-500" : s.tone === "positive" ? "bg-emerald-500" : "bg-amber-500"
                    )}
                  />
                  <div className="min-w-0 leading-tight">
                    <p className="text-xs font-medium">{s.label} — {s.detail}</p>
                    <p className="text-[11px] text-muted-foreground">{s.reasons.join("؛ ")}</p>
                  </div>
                </div>
              ))}
            </div>
          </GlassCard>

          <GlassCard className="border-primary/30 bg-primary/[0.05]">
            <p className="flex items-center gap-1.5 text-xs font-semibold text-primary">
              <Sparkles className="h-3.5 w-3.5" />
              خلاصه هوشمند (از داده واقعی)
            </p>
            <p className="mt-1.5 line-clamp-3 text-xs leading-relaxed text-foreground/90">{f.summary}</p>
          </GlassCard>

          <GlassCard>
            <p className="text-xs font-semibold">اقدام بعدی پیشنهادی سیستم</p>
            <div className="mt-1.5 space-y-1.5">
              {f.actions.map((a) => (
                <div key={a.name} className="flex items-start gap-2 rounded-lg border bg-muted/30 p-1.5">
                  <Lightbulb className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-500" />
                  <div className="min-w-0 leading-tight">
                    <p className="text-xs font-medium">{a.name}</p>
                    <p className="text-[11px] text-muted-foreground">{a.reason}</p>
                  </div>
                </div>
              ))}
            </div>
          </GlassCard>
        </div>
      </div>
    </SlideShell>
  );
}

/* ==================================================== 6 · Business impact */

function ImpactSlide() {
  const im = PITCH.impact;
  return (
    <SlideShell>
      <Eyebrow>مقیاس و اثر</Eyebrow>
      <SlideTitle>آنچه از داده واقعی دیده می‌شود.</SlideTitle>
      <SlideSub>
        {withDot("پوشش کامل پرتفوی، و ریسک‌ها و فرصت‌هایی که بدون سیستم دیده نمی‌شوند")}
      </SlideSub>

      <div className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <BigStat value={formatNumber(im.customers)} label="مشتری تحلیل‌شده" sub="پوشش کامل پرتفوی" accent="text-primary" />
        <BigStat value={formatCompact(im.revenue)} label="تومان درآمد کل" sub={`${formatNumber(PITCH.kpis.salesRows)} ردیف فروش`} accent="text-indigo-500" />
        <BigStat
          value={formatCompact(im.atRiskRevenue)}
          label="تومان درآمد در خطر"
          sub={`${formatNumber(im.atRiskCount)} مشتری پرریسک (موتور ریسک)`}
          accent="text-red-500"
        />
        <BigStat
          value={formatCompact(im.winbackRevenue)}
          label="تومان قابل بازیابی"
          sub={`${formatNumber(im.winbackCount)} مشتری بیش از ۱ سال بدون خرید`}
          accent="text-emerald-500"
        />
      </div>

      <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <GlassCard className="animate-fade-in-up">
          <p className="font-display text-2xl font-extrabold tabular-nums">{formatNumber(PITCH.kpis.complaints)}</p>
          <p className="mt-0.5 text-xs text-muted-foreground">
            شکایت ثبت‌شده · <span className="font-medium text-amber-600 dark:text-amber-400">{formatNumber(PITCH.kpis.openComplaints)} باز</span>
          </p>
        </GlassCard>
        <GlassCard className="animate-fade-in-up">
          <p className="font-display text-2xl font-extrabold tabular-nums">{formatCompact(im.overdue)}</p>
          <p className="mt-0.5 text-xs text-muted-foreground">تومان مطالبات با تأخیر · {formatNumber(im.bouncedChecks)} چک برگشتی</p>
        </GlassCard>
        <GlassCard className="animate-fade-in-up">
          <p className="font-display text-2xl font-extrabold tabular-nums text-red-500">{formatNumber(PITCH.complaintImpact.declinePct)}٪</p>
          <p className="mt-0.5 text-xs text-muted-foreground">
            از {formatNumber(PITCH.complaintImpact.customers)} مشتریِ دارای شکایت، خرید پس از شکایت کاهش یافته است
          </p>
        </GlassCard>
        <GlassCard className="animate-fade-in-up">
          <p className="font-display text-2xl font-extrabold tabular-nums text-emerald-500">{formatNumber(PITCH.kpis.offersAccepted)}</p>
          <p className="mt-0.5 text-xs text-muted-foreground">
            پیشنهاد پذیرفته‌شده از {formatNumber(PITCH.kpis.offers)} پیشنهاد
          </p>
        </GlassCard>
      </div>
      <RealDataNote />
    </SlideShell>
  );
}

/* ==================================================== 7 · Top-K actions */

function TopKSlide() {
  return (
    <SlideShell>
      <Eyebrow>اولویت اقدام</Eyebrow>
      <SlideTitle>سیستم فقط نمی‌گوید چه شد؛ می‌گوید کجا اول اقدام کنیم.</SlideTitle>
      <SlideSub>
        {withDot("رتبه‌بندی ریسک از موتور سیگنال و اقدام پیشنهادی از موتور تصمیم — هر دو از خروجی‌های محاسبه‌شده سامانه")}
      </SlideSub>

      <div className="mt-6 grid gap-4 lg:grid-cols-5">
        {/* Top-K table */}
        <GlassCard className="animate-fade-in-up lg:col-span-3">
          <p className="flex items-center gap-2 text-sm font-semibold">
            <ShieldAlert className="h-4 w-4 text-red-500" />
            امروز با این مشتری‌ها تماس بگیرید
          </p>
          <div className="mt-3 overflow-hidden rounded-xl border">
            <table className="w-full text-right text-xs">
              <thead className="bg-muted text-muted-foreground">
                <tr>
                  <th className="px-3 py-2 font-semibold">مشتری</th>
                  <th className="px-3 py-2 font-semibold">درآمد</th>
                  <th className="px-3 py-2 font-semibold">شکایت باز</th>
                  <th className="px-3 py-2 font-semibold">آخرین خرید</th>
                  <th className="px-3 py-2 font-semibold">اقدام پیشنهادی</th>
                </tr>
              </thead>
              <tbody>
                {PITCH.topRetain.map((r) => (
                  <tr key={r.id} className="border-t align-top">
                    <td className="px-3 py-2.5 font-medium tabular-nums">{r.id}</td>
                    <td className="px-3 py-2.5 font-medium tabular-nums">{formatCompact(r.revenue)}</td>
                    <td className="px-3 py-2.5 tabular-nums">{formatNumber(r.openComplaints)}</td>
                    <td className="px-3 py-2.5 tabular-nums text-muted-foreground">{formatNumber(r.daysSince)} روز</td>
                    <td className="px-3 py-2.5">
                      <span className="inline-block rounded-md bg-amber-500/10 px-2 py-1 text-[11px] font-medium text-amber-600 dark:text-amber-400">
                        {r.action}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="mt-2 text-[11px] text-muted-foreground">
            دلیل هر ردیف از داده واقعی: {PITCH.topRetain[0].reason} · {PITCH.topRetain[1].reason}
          </p>
        </GlassCard>

        {/* Recommendations */}
        <div className="flex flex-col gap-3 lg:col-span-2">
          {PITCH.recommendations.slice(0, 4).map((rec, i) => {
            const Icon = rec.tone === "positive" ? TrendingUp : rec.tone === "warning" ? AlertTriangle : TrendingDown;
            return (
              <GlassCard
                key={rec.title}
                className={cn(
                  "animate-fade-in-up",
                  rec.tone === "positive" && "border-emerald-500/30 bg-emerald-500/[0.06]",
                  rec.tone === "warning" && "border-amber-500/30 bg-amber-500/[0.06]",
                  rec.tone === "negative" && "border-red-500/30 bg-red-500/[0.06]"
                )}
                style={stagger(i)}
              >
                <div className="flex items-start gap-2.5">
                  <span
                    className={cn(
                      "flex h-8 w-8 shrink-0 items-center justify-center rounded-lg",
                      rec.tone === "positive" && "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400",
                      rec.tone === "warning" && "bg-amber-500/10 text-amber-600 dark:text-amber-400",
                      rec.tone === "negative" && "bg-red-500/10 text-red-600 dark:text-red-400"
                    )}
                  >
                    <Icon className="h-4 w-4" />
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="text-xs font-semibold leading-snug">{rec.title}</p>
                    <p className="mt-0.5 text-[11px] leading-relaxed text-muted-foreground">{rec.detail}</p>
                  </div>
                </div>
              </GlassCard>
            );
          })}
        </div>
      </div>
      <RealDataNote />
    </SlideShell>
  );
}

/* ==================================================== 8 · Charts & evidence */

function TrendChart() {
  return (
    <GlassCard className="animate-fade-in-up p-3">
      <p className="text-sm font-semibold">روند فروش ماهانه</p>
      <p className="text-[11px] text-muted-foreground">دوره اصلی فعالیت در داده‌های سامانه (مبالغ کل)</p>
      <div dir="ltr" className="mt-2 h-[120px]">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={PITCH.purchaseTrend} margin={{ top: 4, right: 4, left: 4, bottom: 0 }}>
            <defs>
              <linearGradient id="pitchSaleGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="var(--chart-primary)" stopOpacity={0.35} />
                <stop offset="100%" stopColor="var(--chart-primary)" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" className="stroke-border" vertical={false} />
            <XAxis dataKey="month" tickLine={false} axisLine={false} tick={{ fontSize: 9 }} interval="preserveStartEnd" className="text-muted-foreground" />
            <YAxis tickLine={false} axisLine={false} tick={{ fontSize: 9 }} className="text-muted-foreground" tickFormatter={(v) => formatCompact(Number(v))} />
            <Tooltip contentStyle={{ borderRadius: 8, border: "1px solid hsl(var(--border))", fontSize: 12 }} formatter={(v) => [formatCompact(Number(v)), "مبلغ کل"]} />
            <Area type="monotone" dataKey="value" stroke="var(--chart-primary)" strokeWidth={2} fill="url(#pitchSaleGrad)" />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </GlassCard>
  );
}

function SeverityChart() {
  return (
    <GlassCard className="animate-fade-in-up p-3">
      <p className="text-sm font-semibold">شدت شکایات</p>
      <p className="text-[11px] text-muted-foreground">توزیع ۵۲۰ شکایت ثبت‌شده</p>
      <div className="mt-2 flex items-center justify-center">
        <div className="h-36 w-36 shrink-0">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={PITCH.complaintSeverity}
                dataKey="value"
                nameKey="name"
                innerRadius={36}
                outerRadius={56}
                paddingAngle={2}
              >
                {PITCH.complaintSeverity.map((d, i) => (
                  <Cell key={d.name} fill={pieColors[i % pieColors.length]} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{ borderRadius: 8, border: "1px solid hsl(var(--border))", fontSize: 12 }}
                formatter={(v) => [formatNumber(Number(v)), "شکایت"]}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>
        <div className="min-w-0 flex-1 space-y-1.5 pr-3">
          {PITCH.complaintSeverity.map((d, i) => (
            <div key={d.name} className="flex items-center justify-between gap-2 text-xs">
              <span className="flex items-center gap-1.5 text-muted-foreground">
                <span className="h-2 w-2 rounded-full" style={{ background: pieColors[i % pieColors.length] }} />
                {d.name}
              </span>
              <span className="font-medium tabular-nums">{formatNumber(d.value)}</span>
            </div>
          ))}
        </div>
      </div>
    </GlassCard>
  );
}

function OfferChart() {
  return (
    <GlassCard className="animate-fade-in-up p-3">
      <p className="text-sm font-semibold">اثربخشی پیشنهادها</p>
      <p className="text-[11px] text-muted-foreground">نرخ پذیرش بر اساس نوع پیشنهاد</p>
      <div className="mt-2.5 space-y-2">
        {PITCH.offerEffectiveness.map((o) => (
          <div key={o.type} className="flex items-center justify-between gap-3">
            <p className="w-20 text-xs font-medium">
              {o.type}
              <span className="block text-[10px] text-muted-foreground">{formatNumber(o.count)} پیشنهاد</span>
            </p>
            <div className="h-2 flex-1 overflow-hidden rounded-full bg-muted">
              <div className="h-full rounded-full bg-emerald-500/70" style={{ width: `${o.rate * 100}%` }} />
            </div>
            <span className="w-10 text-left text-xs font-semibold tabular-nums">{formatNumber(Math.round(o.rate * 100))}٪</span>
          </div>
        ))}
      </div>
      <div className="mt-3 rounded-xl border bg-amber-500/[0.06] p-2.5">
        <p className="text-xs font-semibold text-amber-600 dark:text-amber-400">پرتکرارترین موضوع شکایت: «فیلامنت و پرز» — ۴۵ شکایت</p>
        <p className="mt-1 text-[11px] leading-relaxed text-muted-foreground">
          کیفیت محصول، پرتکرارترین درد مشتریان است؛ موضوعی که در پیشنهاد اقدام سامانه هم اولویت گرفته است.
        </p>
      </div>
    </GlassCard>
  );
}

function EvidenceSlide() {
  return (
    <SlideShell className="py-3 md:py-4">
      <Eyebrow>شواهد و نمودار</Eyebrow>
      <SlideTitle className="mt-2">روندها و توزیع‌ها — از داده واقعی.</SlideTitle>
      <SlideSub className="mt-1.5">
        {withDot("همان نمودارهای داخل محصول، با همان داده‌ها")}
      </SlideSub>

      <div className="mt-3 grid gap-3 lg:grid-cols-2">
        <div className="lg:col-span-2">
          <TrendChart />
        </div>
        <SeverityChart />
        <OfferChart />
      </div>

      <GlassCard className="mt-2.5 flex items-center gap-3 border-red-500/25 bg-red-500/[0.05] py-2">
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-red-500/10 text-red-500">
          <MessageSquareWarning className="h-4.5 w-4.5" />
        </span>
        <p className="text-xs leading-relaxed md:text-sm">
          <span className="font-bold text-red-600 dark:text-red-400">{formatNumber(PITCH.complaintImpact.declinePct)}٪</span>{" "}
          از {formatNumber(PITCH.complaintImpact.customers)} مشتری‌ای که شکایت داشته‌اند، پس از شکایت خرید کمتری داشته‌اند —
          رابطه‌ای که در هیچ گزارش فروش سنتی دیده نمی‌شود.
        </p>
      </GlassCard>
    </SlideShell>
  );
}

/* ==================================================== 9 · Copilot */

function ChatBubble({ role, children }: { role: "user" | "assistant"; children: ReactNode }) {
  if (role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[85%] rounded-2xl rounded-tr-sm bg-primary px-3.5 py-1.5 text-xs leading-relaxed text-primary-foreground">
          {children}
        </div>
      </div>
    );
  }
  return (
    <div className="flex gap-2">
      <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 to-violet-500 text-white">
        <Sparkles className="h-3.5 w-3.5" />
      </span>
      <div className="min-w-0 flex-1 space-y-2">{children}</div>
    </div>
  );
}

function ChatTable() {
  return (
    <div className="overflow-hidden rounded-xl border">
      <table className="w-full text-right text-[11px]">
        <thead className="bg-muted text-muted-foreground">
          <tr>
            <th className="px-2.5 py-1 font-semibold">مشتری</th>
            <th className="px-2.5 py-1 font-semibold">درآمد</th>
            <th className="px-2.5 py-1 font-semibold">چرا الان</th>
            <th className="px-2.5 py-1 font-semibold">اقدام</th>
          </tr>
        </thead>
        <tbody>
          {PITCH.copilot.a1Rows.map((r) => (
            <tr key={r.id} className="border-t">
              <td className="px-2.5 py-1 font-medium tabular-nums">{r.id}</td>
              <td className="px-2.5 py-1 tabular-nums">{r.revenue}</td>
              <td className="px-2.5 py-1 text-muted-foreground">{r.signal}</td>
              <td className="px-2.5 py-1">
                <span className="rounded-md bg-amber-500/10 px-1.5 py-0.5 font-medium text-amber-600 dark:text-amber-400">
                  {r.action}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function CopilotSlide() {
  const c = PITCH.copilot;
  return (
    <SlideShell className="py-3 md:py-4">
      <Eyebrow>کوپایلوت</Eyebrow>
      <SlideTitle className="mt-2">تحلیل را به اقدام تبدیل کن.</SlideTitle>
      <SlideSub className="mt-1.5">{withDot(c.intro)}</SlideSub>

      <div className="mx-auto mt-3 w-full max-w-4xl">
        <GlassCard className="overflow-hidden p-0">
          {/* chat header */}
          <div className="flex h-9 items-center gap-2 border-b px-4">
            <span className="flex h-7 w-7 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 to-violet-500 text-white">
              <Sparkles className="h-3.5 w-3.5" />
            </span>
            <div className="flex min-w-0 flex-col leading-tight">
              <span className="text-xs font-semibold">Cust Intel</span>
              <span className="inline-flex items-center gap-1 text-[10px] text-emerald-500">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                متصل · سیستم + هوش مصنوعی
              </span>
            </div>
            <span className="mr-auto hidden rounded-full border bg-background px-3 py-1 text-[10px] text-muted-foreground sm:inline-flex">
              پاسخ از نتایج از پیش‌محاسبه‌شده
            </span>
          </div>

          {/* messages */}
          <div className="space-y-2 px-4 py-2">
            <ChatBubble role="user">{c.q1}</ChatBubble>
            <ChatBubble role="assistant">
              <p className="text-xs font-semibold">{c.a1Title}</p>
              <ChatTable />
              <p className="text-[11px] text-muted-foreground">
                این رتبه‌بندی از موتور ریسک (سیگنال‌های واقعی) و اقدام از موتور تصمیم سامانه گرفته شده است.
              </p>
            </ChatBubble>

            <ChatBubble role="user">{c.q2}</ChatBubble>
            <ChatBubble role="assistant">
              <div className="space-y-1">
                {c.a2.map((line) => (
                  <p key={line} className="flex items-start gap-1.5 text-[11px] leading-relaxed text-foreground/90">
                    <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-primary/70" />
                    {line}
                  </p>
                ))}
              </div>
            </ChatBubble>

            <ChatBubble role="user">{c.q3}</ChatBubble>
            <ChatBubble role="assistant">
              <div className="space-y-1">
                {c.a3.map((a) => (
                  <div key={a.name} className="flex items-start gap-2 rounded-lg border bg-muted/30 p-1.5">
                    <Lightbulb className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-500" />
                    <div className="min-w-0 leading-tight">
                      <p className="text-[11px] font-medium">{a.name}</p>
                      <p className="text-[10px] text-muted-foreground">{a.next}</p>
                    </div>
                  </div>
                ))}
              </div>
            </ChatBubble>
          </div>
        </GlassCard>
      </div>
    </SlideShell>
  );
}

/* ==================================================== 10 · Why different */

function FlowBoxes({ items, active }: { items: string[]; active?: boolean }) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      {items.map((item, i) => (
        <div key={item} className="flex items-center gap-2">
          <span
            className={cn(
              "rounded-xl border px-3 py-2 text-xs font-medium",
              active
                ? "border-primary/50 bg-primary/[0.08] text-foreground"
                : "border bg-muted/40 text-muted-foreground"
            )}
          >
            {item}
          </span>
          {i < items.length - 1 && <ArrowLeft className="h-4 w-4 shrink-0 text-primary/50" />}
        </div>
      ))}
    </div>
  );
}

function DifferentSlide() {
  const f = PITCH.featured;
  return (
    <SlideShell>
      <Eyebrow>تفاوت</Eyebrow>
      <SlideTitle>از اطلاعات مشتری به تصمیم مشتری.</SlideTitle>
      <SlideSub>
        {withDot("سیستم ما گزارش نمی‌سازد؛ زنجیره‌ای از داده تا اقدام می‌سازد — و هر حلقه قابل توضیح است")}
      </SlideSub>

      <div className="mt-8 space-y-4">
        <div>
          <p className="mb-2 text-xs font-semibold text-muted-foreground">CRM سنتی</p>
          <FlowBoxes items={["داده", "گزارش", "تحلیل انسانی", "تصمیم"]} />
        </div>
        <div>
          <p className="mb-2 flex items-center gap-2 text-xs font-semibold text-primary">
            <span className="flex h-5 w-5 items-center justify-center rounded-md bg-gradient-to-br from-indigo-500 to-fuchsia-500 text-white">
              <Rocket className="h-3 w-3" />
            </span>
            بینش مشتری
          </p>
          <FlowBoxes active items={["داده", "مشتری ۳۶۰", "سیگنال", "ریسک + فرصت", "پیشنهاد", "اقدام"]} />
        </div>
      </div>

      <GlassCard className="mt-7 flex flex-col gap-3 border-primary/25 bg-primary/[0.05] md:flex-row md:items-center">
        <div className="flex items-center gap-3 md:w-56 md:shrink-0">
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 to-violet-500 text-white">
            <ShoppingCart className="h-5 w-5" />
          </span>
          <div className="leading-tight">
            <p className="text-sm font-semibold tabular-nums">{f.id}</p>
            <p className="text-[11px] text-muted-foreground">مثال واقعی</p>
          </div>
        </div>
        <div className="min-w-0 flex-1 space-y-1.5 text-xs">
          <p className="flex flex-wrap items-center gap-x-2 gap-y-1">
            <span className="font-semibold text-emerald-600 dark:text-emerald-400">درآمد ۱۶۶٫۸ میلیون</span>
            <ArrowLeft className="h-3.5 w-3.5 text-muted-foreground" />
            <span className="text-muted-foreground">سیگنال: چرخه خرید بحرانی (۱٬۵۷۰ روز) + اثر شکایت (۶۸٪-)</span>
            <ArrowLeft className="h-3.5 w-3.5 text-muted-foreground" />
            <span className="font-semibold text-amber-600 dark:text-amber-400">اقدام: رسیدگی به شکایت‌ها</span>
          </p>
          <p className="text-muted-foreground/90">
            این زنجیره برای هر ۶۴۴ مشتری قابل توضیح است — نه یک عدد، بلکه «چرا» و «چه باید کرد».
          </p>
        </div>
      </GlassCard>
    </SlideShell>
  );
}

/* ==================================================== 11 · Closing + team */

function ClosingSlide() {
  return (
    <SlideShell className="items-center text-center">
      <span className="inline-flex items-center gap-2 rounded-full border border-primary/30 bg-primary/10 px-4 py-1.5 text-xs font-semibold uppercase tracking-[0.25em] text-primary">
        <Sparkles className="h-3.5 w-3.5" />
        جمع‌بندی
      </span>
      <h2 className="mt-5 max-w-4xl font-display text-3xl font-extrabold leading-tight tracking-tight md:text-5xl">
        آینده CRM داشبورد بیشتر نیست؛
        <br />
        دانستن اینکه <span className="deck-gradient-text">کدام مشتری</span> به توجه نیاز دارد،{" "}
        <span className="text-primary">چرا</span>، و <span className="text-primary">چه باید کرد</span>.
      </h2>
      <p className="mx-auto mt-4 max-w-2xl text-sm text-muted-foreground md:text-base">
        {withDot("بینش مشتری داده‌های پراکنده شما را به سیگنال، ریسک، فرصت و اقدام بعدی تبدیل می‌کند — همه قابل توضیح و از داده واقعی")}
      </p>

      {/* team */}
      <div className="mt-8 w-full max-w-3xl">
        <p className="mb-3 text-xs font-semibold uppercase tracking-widest text-muted-foreground">تیم</p>
        <div className="grid gap-3 sm:grid-cols-3">
          {PITCH.team.map((m, i) => (
            <GlassCard key={m.name} className="animate-fade-in-up text-center" style={stagger(i)}>
              <span className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-indigo-500 to-violet-500 font-display text-base font-bold text-white">
                {m.name.trim().charAt(0)}
              </span>
              <p className="mt-3 font-display text-sm font-semibold">{m.name}</p>
              <p className="mt-1 text-xs leading-relaxed text-muted-foreground">{m.role}</p>
            </GlassCard>
          ))}
        </div>
        <p className="mt-6 text-xs text-muted-foreground/80">{PITCH.productName} · داده واقعی · محاسبه‌شده · قابل توضیح</p>
      </div>
    </SlideShell>
  );
}

/* ------------------------------------------------------------- export */

export interface DeckSlide {
  id: string;
  label: string;
  /** Suggested speaking duration in seconds (presenter aid). */
  duration: number;
  render: () => ReactNode;
}

export const PITCH_SLIDES: DeckSlide[] = [
  { id: "cover", label: "جلد", duration: 15, render: () => <CoverSlide /> },
  { id: "problem", label: "مسئله", duration: 40, render: () => <ProblemSlide /> },
  { id: "insight", label: "ایده", duration: 25, render: () => <InsightSlide /> },
  { id: "product", label: "محصول", duration: 40, render: () => <ProductSlide /> },
  { id: "customer", label: "مشتری واقعی", duration: 55, render: () => <CustomerStorySlide /> },
  { id: "impact", label: "اثر", duration: 55, render: () => <ImpactSlide /> },
  { id: "topk", label: "اولویت اقدام", duration: 55, render: () => <TopKSlide /> },
  { id: "evidence", label: "شواهد", duration: 55, render: () => <EvidenceSlide /> },
  { id: "copilot", label: "کوپایلوت", duration: 60, render: () => <CopilotSlide /> },
  { id: "different", label: "تفاوت", duration: 30, render: () => <DifferentSlide /> },
  { id: "closing", label: "پایان", duration: 25, render: () => <ClosingSlide /> },
];
