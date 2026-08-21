import { useEffect, useRef, useState } from "react";
import {
  AlertTriangle,
  BadgeCheck,
  DollarSign,
  Landmark,
  Loader2,
  MessageSquareWarning,
  PieChart as PieChartIcon,
  RefreshCw,
  Sparkles,
  Target,
  TrendingDown,
  TrendingUp,
  Users,
} from "lucide-react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  CartesianGrid,
} from "recharts";

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  fetchDashboard,
  fetchDashboardIntelligence,
  type DashboardData,
  type KpiValue,
  type IncomeRecommendation,
  type DistributionSlice,
  type SummaryStatus,
} from "@/lib/api";
import { formatCompact, formatCurrency, formatNumber, withDot, cn } from "@/lib/utils";
import { SectionCard } from "@/components/section-card";
import { SummaryText } from "@/components/summary-text";

const kpiIcons: Record<string, typeof Users> = {
  "کل مشتریان": Users,
  "درآمد کل": DollarSign,
  "سفارش‌ها": Users,
  "شکایات": MessageSquareWarning,
};

const pieColors = ["#6366f1", "#8b5cf6", "#10b981", "#f59e0b", "#ef4444", "#06b6d4"];

const LOADER_TEXTS = [
  "در حال تحلیل وضعیت کلی کسب‌وکار…",
  "در حال بررسی مشتریان پرریسک…",
  "در حال بررسی شکایات و فرصت‌های رشد…",
  "در حال آماده‌سازی پیشنهادها…",
  "کمی صبر کنید؛ تحلیل کلی در حال آماده شدن است…",
];

/* ---------------------------------------------------------------- pieces */

function KpiCard({ kpi, index }: { kpi: KpiValue; index: number }) {
  const Icon = kpiIcons[kpi.label] ?? Users;
  return (
    <Card className="animate-fade-in-up" style={{ animationDelay: `${index * 60}ms` }}>
      <CardContent className="p-6">
        <div className="flex items-start justify-between">
          <p className="text-sm font-medium text-muted-foreground">{kpi.label}</p>
          <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10 text-primary">
            <Icon className="h-4 w-4" />
          </span>
        </div>
        <div className="mt-4 flex items-end justify-between">
          <p className="text-2xl font-semibold tabular-nums tracking-tight">{formatCompact(kpi.value)}</p>
          {kpi.change && (
            <span className="inline-flex items-center gap-0.5 rounded-md px-1.5 py-0.5 text-xs font-medium">
              {kpi.change}
            </span>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

function SummaryLoader() {
  const [idx, setIdx] = useState(0);
  useEffect(() => {
    const t = setInterval(() => setIdx((v) => (v + 1) % LOADER_TEXTS.length), 2200);
    return () => clearInterval(t);
  }, []);
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin text-primary" />
        <span key={idx} className="animate-fade-in-up">
          {LOADER_TEXTS[idx]}
        </span>
      </div>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
        <div className="h-full w-1/2 animate-pulse rounded-full bg-primary/40" />
      </div>
    </div>
  );
}

function RecommendationCard({ rec, wide }: { rec: IncomeRecommendation; wide?: boolean }) {
  const icon =
    rec.tone === "positive" ? <TrendingUp className="h-4 w-4" /> : rec.tone === "warning" ? <AlertTriangle className="h-4 w-4" /> : <TrendingDown className="h-4 w-4" />;
  return (
    <div
      className={cn(
        "flex h-full flex-col rounded-xl border p-4 backdrop-blur-md transition-colors",
        rec.tone === "positive" && "border-emerald-500/30 bg-emerald-500/10",
        rec.tone === "warning" && "border-amber-500/30 bg-amber-500/10",
        rec.tone === "negative" && "border-red-500/30 bg-red-500/10"
      )}
    >
      <div className="flex items-start gap-3">
        <span
          className={cn(
            "flex h-8 w-8 shrink-0 items-center justify-center rounded-lg",
            rec.tone === "positive" && "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400",
            rec.tone === "warning" && "bg-amber-500/10 text-amber-600 dark:text-amber-400",
            rec.tone === "negative" && "bg-red-500/10 text-red-600 dark:text-red-400"
          )}
        >
          {icon}
        </span>
        <div className="min-w-0 flex-1 space-y-1">
          <p className="text-sm font-semibold leading-snug">{rec.title}</p>
          <p className={cn("text-xs leading-relaxed text-muted-foreground", wide && "md:text-sm")}>{rec.detail}</p>
        </div>
      </div>
      {rec.impact > 0 && (
        <p className="mt-3 border-t pt-2 text-xs font-medium tabular-nums text-muted-foreground">
          تأثیر: {formatCurrency(rec.impact)} تومان
        </p>
      )}
    </div>
  );
}

const riskChip: Record<string, string> = {
  زیاد: "bg-red-500/10 text-red-600 dark:text-red-400",
  متوسط: "bg-amber-500/10 text-amber-600 dark:text-amber-400",
  کم: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400",
};

/* ------------------------------------------------------------- charts */

function PurchaseTrendChart({ data }: { data: DashboardData["purchaseTrend"] }) {
  return (
    <Card className="h-full animate-fade-in-up" style={{ animationDelay: "240ms" }}>
      <CardHeader>
        <CardTitle className="text-base">روند فروش</CardTitle>
        <CardDescription>{withDot("حجم فروش ماهانه (مبالغ کل)")}</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data} margin={{ top: 4, right: 4, left: -16, bottom: 0 }}>
              <defs>
                <linearGradient id="purchaseGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="var(--chart-primary)" stopOpacity={0.35} />
                  <stop offset="100%" stopColor="var(--chart-primary)" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" className="stroke-border" vertical={false} />
              <XAxis dataKey="month" tickLine={false} axisLine={false} tick={{ fontSize: 10 }} interval="preserveStartEnd" className="text-muted-foreground" />
              <YAxis tickLine={false} axisLine={false} tick={{ fontSize: 10 }} className="text-muted-foreground" tickFormatter={(v) => formatCompact(Number(v))} />
              <Tooltip contentStyle={{ borderRadius: 8, border: "1px solid hsl(var(--border))", fontSize: 12 }} formatter={(v) => [formatCompact(Number(v)), "مبلغ کل"]} />
              <Area type="monotone" dataKey="value" stroke="var(--chart-primary)" strokeWidth={2} fill="url(#purchaseGrad)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}

function ComplaintTrendChart({ data }: { data: DashboardData["complaintTrend"] }) {
  return (
    <Card className="h-full animate-fade-in-up" style={{ animationDelay: "300ms" }}>
      <CardHeader>
        <CardTitle className="text-base">روند شکایات</CardTitle>
        <CardDescription>{withDot("شکایات ثبت‌شده در هر ماه")}</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data} margin={{ top: 4, right: 4, left: -24, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-border" vertical={false} />
              <XAxis dataKey="month" tickLine={false} axisLine={false} tick={{ fontSize: 10 }} interval="preserveStartEnd" className="text-muted-foreground" />
              <YAxis tickLine={false} axisLine={false} tick={{ fontSize: 10 }} className="text-muted-foreground" />
              <Tooltip cursor={{ fill: "hsl(var(--muted))" }} contentStyle={{ borderRadius: 8, border: "1px solid hsl(var(--border))", fontSize: 12 }} />
              <Bar dataKey="value" radius={[4, 4, 0, 0]} fill="var(--chart-warning)" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}

function MiniDistribution({ title, data }: { title: string; data: DistributionSlice[] }) {
  if (data.length === 0) {
    return (
      <div>
        <p className="mb-2 text-xs font-semibold text-muted-foreground">{title}</p>
        <p className="rounded-lg border border-dashed p-4 text-center text-xs text-muted-foreground">
          داده‌ای موجود نیست
        </p>
      </div>
    );
  }
  return (
    <div>
      <p className="mb-3 text-xs font-semibold text-muted-foreground">{title}</p>
      <div className="flex items-center gap-5">
        <div className="h-36 w-36 shrink-0">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie data={data} dataKey="value" nameKey="name" innerRadius={38} outerRadius={62} paddingAngle={2}>
                {data.map((entry, i) => (
                  <Cell key={entry.name} fill={pieColors[i % pieColors.length]} />
                ))}
              </Pie>
              <Tooltip contentStyle={{ borderRadius: 8, border: "1px solid hsl(var(--border))", fontSize: 12 }} formatter={(v) => [formatCompact(Number(v)), "تعداد"]} />
            </PieChart>
          </ResponsiveContainer>
        </div>
        <div className="min-w-0 flex-1 space-y-2.5">
          {data.map((d, i) => (
            <div key={d.name} className="flex items-center justify-between gap-3 text-xs">
              <span className="flex min-w-0 items-center gap-2 text-muted-foreground">
                <span className="h-2 w-2 shrink-0 rounded-full" style={{ background: pieColors[i % pieColors.length] }} />
                <span className="truncate">{d.name}</span>
              </span>
              <span className="shrink-0 font-medium tabular-nums">{formatCompact(d.value)}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function CombinedDistribution({ data }: { data: DashboardData }) {
  return (
    <Card className="h-full animate-fade-in-up" style={{ animationDelay: "360ms" }}>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <PieChartIcon className="h-4 w-4 text-muted-foreground" />
          ترکیب مشتریان
        </CardTitle>
        <CardDescription>{withDot("بخش بازار و وضعیت مشتریان در یک نگاه")}</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 gap-8 lg:grid-cols-2 lg:gap-12">
          <MiniDistribution title="بخش بازار (سگمنت)" data={data.segmentDistribution} />
          <MiniDistribution title="وضعیت مشتری" data={data.statusDistribution} />
        </div>
      </CardContent>
    </Card>
  );
}

/* ----------------------------------------------------------------- main */

export function Dashboard() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [summary, setSummary] = useState<SummaryStatus | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const stopPollRef = useRef<() => void>(() => {});

  useEffect(() => {
    stopPollRef.current();
    stopPollRef.current = () => {};
    fetchDashboard().then(setData).catch(() => setError("امکان بارگذاری داده‌ها وجود ندارد"));
    // Read the cached summary only — never trigger regeneration on load.
    fetchDashboardIntelligence()
      .then((res) => {
        if (res.status === "ready") setSummary(res);
        else setSummary(null);
      })
      .catch(() => setSummary(null));
    return () => stopPollRef.current();
  }, []);

  function refreshSummary() {
    setRefreshing(true);
    // The backend waits for the regeneration to finish, so a single request
    // is enough — no polling loop.
    fetchDashboardIntelligence(true)
      .then((res) => {
        if (res.status === "ready") setSummary(res);
        setRefreshing(false);
      })
      .catch(() => setRefreshing(false));
  }

  if (error) {
    return (
      <div className="flex h-full items-center justify-center pt-20">
        <p className="text-sm text-muted-foreground">{error}</p>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="space-y-6">
        <div className="flex flex-col gap-1 pt-4">
          <h1 className="text-2xl font-semibold tracking-tight">داشبورد</h1>
          <p className="text-sm text-muted-foreground">{withDot("نمای کلی عملکرد، فروش و وضعیت مشتریان کسب‌وکار")}</p>
        </div>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {[0, 1, 2, 3].map((i) => (
            <div key={i} className="h-32 animate-pulse rounded-xl border bg-muted/50" />
          ))}
        </div>
        <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
          <div className="h-72 animate-pulse rounded-xl border bg-muted/50" />
          <div className="h-72 animate-pulse rounded-xl border bg-muted/50" />
        </div>
      </div>
    );
  }

  const intel = data.intelligence;
  const summaryText = summary?.status === "ready" ? summary.summary : null;
  const maxTheme = intel.complaint_themes.length ? Math.max(...intel.complaint_themes.map((t) => t.count)) : 1;
  const levelOf = (score: number) => (score >= 65 ? "زیاد" : score >= 35 ? "متوسط" : "کم");

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-1 pt-4">
        <h1 className="text-2xl font-semibold tracking-tight">داشبورد</h1>
        <p className="text-sm text-muted-foreground">{withDot("نمای کلی عملکرد، فروش و وضعیت مشتریان کسب‌وکار")}</p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {data.kpis.map((kpi, i) => (
          <KpiCard key={kpi.label} kpi={kpi} index={i} />
        ))}
      </div>

      {/* LLM overall analysis — cached; regenerated only on refresh */}
      <Card className="border-primary/30 bg-gradient-to-br from-primary/5 to-transparent">
        <CardHeader className="pb-2">
          <div className="flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-primary" />
            <CardTitle className="text-sm">تحلیل کلی هوشمند</CardTitle>
            {summaryText && !refreshing && (
              <Badge variant="outline" className="mr-auto gap-1 border-transparent bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
                <BadgeCheck className="h-3 w-3" />
                آماده
              </Badge>
            )}
            <Button variant="ghost" size="sm" className="gap-1 text-muted-foreground" onClick={refreshSummary} disabled={refreshing} title="محاسبه دوباره تحلیل کلی">
              <RefreshCw className={cn("h-3.5 w-3.5", refreshing && "animate-spin")} />
              تازه‌سازی
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {refreshing ? (
            <SummaryLoader />
          ) : summaryText ? (
            <SummaryText text={summaryText} />
          ) : (
            <div className="flex flex-col items-start gap-3">
              <p className="text-sm text-muted-foreground">
                با کلیک روی «تازه‌سازی»، تحلیل کلی هوشمند از روی داده‌های واقعی محاسبه می‌شود.
              </p>
              <Button size="sm" onClick={refreshSummary}>
                <Sparkles className="mr-1 h-3.5 w-3.5" />
                آماده‌سازی تحلیل
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Income recommendations — 4 compact + 1 full-width (no empty slot) */}
      <div>
        <div className="mb-3 flex items-center gap-2">
          <Target className="h-4 w-4 text-primary" />
          <h2 className="text-base font-semibold">پیشنهادها برای درآمد بهتر</h2>
        </div>
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          {data.recommendations.map((rec, i) => {
            const wide = i === data.recommendations.length - 1 && data.recommendations.length % 2 === 1;
            return (
              <div key={rec.id} className={cn(wide && "lg:col-span-2")}>
                <RecommendationCard rec={rec} wide={wide} />
              </div>
            );
          })}
        </div>
      </div>

      {/* Trend charts */}
      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <PurchaseTrendChart data={data.purchaseTrend} />
        <ComplaintTrendChart data={data.complaintTrend} />
      </div>

      {/* Merged distribution card */}
      <CombinedDistribution data={data} />

      {/* Overall analysis sections — varied responsive widths */}
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-12">
        <div className="xl:col-span-7">
          <SectionCard
            icon={AlertTriangle}
            title="مشتریان در معرض از دست رفتن"
            count={intel.at_risk.count}
            badge={
              <Badge variant="outline" className="gap-1 border-transparent bg-red-500/10 text-red-600 dark:text-red-400">
                {formatCurrency(intel.at_risk.revenue)} در خطر
              </Badge>
            }
          >
            {intel.at_risk.top.length === 0 ? (
              <p className="rounded-lg border border-dashed p-4 text-center text-xs text-muted-foreground">{withDot("مشتری در معرض از دست رفتنی یافت نشد")}</p>
            ) : (
              <div className="space-y-2">
                {intel.at_risk.top.map((r) => (
                  <div key={r.customer_id} className="flex items-center justify-between gap-3 rounded-lg border bg-muted/30 px-2.5 py-2">
                    <div className="min-w-0 leading-tight">
                      <p className="text-xs font-medium tabular-nums">{r.customer_id}</p>
                      <p className="text-[10px] text-muted-foreground">
                        {formatNumber(r.complaints)} شکایت · {formatNumber(r.orders)} سفارش
                        {r.days_since != null && <span> · آخرین خرید {formatNumber(r.days_since)} روز پیش</span>}
                        {r.bounced > 0 && <span> · {formatNumber(r.bounced)} چک برگشتی</span>}
                      </p>
                    </div>
                    <div className="shrink-0 text-left">
                      <p className="text-xs font-medium tabular-nums">{formatCurrency(r.revenue)}</p>
                      <span className={cn("inline-block rounded-md px-1.5 py-0.5 text-[10px]", riskChip[levelOf(r.risk_score)] ?? riskChip["متوسط"])}>
                        {levelOf(r.risk_score)}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </SectionCard>
        </div>

        <div className="xl:col-span-5">
          <SectionCard
            icon={Landmark}
            title="مطالبات، چک‌های برگشتی و مشتریان قدیمی"
          >
            <div className="space-y-2.5">
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                <div className="rounded-lg border bg-muted/30 p-3 text-center">
                  <p className="text-xl font-semibold tabular-nums">{formatCurrency(intel.collection_risk.overdue)}</p>
                  <p className="mt-1 text-[11px] text-muted-foreground">مطالبات با تأخیر</p>
                </div>
                <div className="rounded-lg border bg-red-500/5 p-3 text-center">
                  <p className="text-xl font-semibold tabular-nums">{formatNumber(intel.collection_risk.bounced)}</p>
                  <p className="mt-1 text-[11px] text-muted-foreground">چک برگشتی</p>
                </div>
                <div className="rounded-lg border bg-emerald-500/5 p-3 text-center">
                  <p className="text-xl font-semibold tabular-nums">{formatNumber(intel.winback.count)}</p>
                  <p className="mt-1 text-[11px] text-muted-foreground">مشتری قدیمی ارزشمند</p>
                </div>
              </div>
              <div className="rounded-lg border bg-muted/30 p-3">
                <p className="text-xs text-muted-foreground">مجموع درآمد قابل بازیابی از مشتریان قدیمی (بیش از یک سال بدون خرید)</p>
                <p className="mt-1 text-lg font-semibold tabular-nums">{formatCurrency(intel.winback.revenue)}</p>
              </div>
              <div className="rounded-lg border bg-muted/30 p-3">
                <p className="mb-2 text-xs text-muted-foreground">بیشترین سهم درآمد بر اساس بخش بازار</p>
                <div className="space-y-2">
                  {intel.segment_share.slice(0, 4).map((s) => (
                    <div key={s.name} className="flex items-center gap-3">
                      <span className="w-16 truncate text-xs text-muted-foreground">{s.name}</span>
                      <div className="h-2 flex-1 overflow-hidden rounded-full bg-muted">
                        <div className="h-full rounded-full bg-primary/70" style={{ width: `${(s.value / (intel.segment_share[0]?.value || 1)) * 100}%` }} />
                      </div>
                      <span className="w-16 text-left text-xs font-medium tabular-nums">{formatCurrency(s.value)}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </SectionCard>
        </div>
        <div className="xl:col-span-6">
          <SectionCard
            bodyHeight="h-48"
            icon={MessageSquareWarning}
            title="موضوع‌های پرتکرار شکایت"
            count={intel.complaint_themes.length}
          >
            {intel.complaint_themes.length === 0 ? (
              <p className="rounded-lg border border-dashed p-4 text-center text-xs text-muted-foreground">{withDot("شکایتی ثبت نشده است")}</p>
            ) : (
              <div className="space-y-2.5">
                {intel.complaint_themes.map((t) => (
                  <div key={t.name} className="flex items-center gap-3">
                    <span className="w-32 truncate text-xs text-muted-foreground">{t.name}</span>
                    <div className="h-2 flex-1 overflow-hidden rounded-full bg-muted">
                      <div className="h-full rounded-full bg-amber-500/70" style={{ width: `${(t.count / maxTheme) * 100}%` }} />
                    </div>
                    <span className="w-10 text-left text-xs font-medium tabular-nums">{formatNumber(t.count)}</span>
                  </div>
                ))}
              </div>
            )}
          </SectionCard>
        </div>

        <div className="xl:col-span-6">
          <SectionCard
            bodyHeight="h-48"
            icon={Target}
            title="اثربخشی پیشنهادها"
            count={intel.offer_effectiveness.length}
          >
            {intel.offer_effectiveness.length === 0 ? (
              <p className="rounded-lg border border-dashed p-4 text-center text-xs text-muted-foreground">{withDot("پیشنهادی ثبت نشده است")}</p>
            ) : (
              <div className="space-y-2.5">
                {intel.offer_effectiveness.map((o) => (
                  <div key={o.type} className="flex items-center justify-between gap-3 rounded-lg border bg-muted/30 px-2.5 py-2">
                    <p className="text-xs font-medium">
                      {o.type}
                      <span className="mr-1 text-[10px] text-muted-foreground">({formatNumber(o.count)} پیشنهاد)</span>
                    </p>
                    <div className="flex items-center gap-2">
                      <div className="h-2 w-20 overflow-hidden rounded-full bg-muted">
                        <div className="h-full rounded-full bg-emerald-500/70" style={{ width: `${o.rate * 100}%` }} />
                      </div>
                      <span className="text-xs font-medium tabular-nums">{formatNumber(Math.round(o.rate * 100))}٪</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </SectionCard>
        </div>

      </div>
    </div>
  );
}