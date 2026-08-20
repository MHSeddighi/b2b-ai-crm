import { useEffect, useRef, useState, type ReactNode } from "react";
import {
  Activity,
  ArrowRight,
  BadgeCheck,
  CalendarClock,
  ClipboardList,
  FileText,
  Handshake,
  Lightbulb,
  Loader2,
  MailQuestion,
  MessageSquareWarning,
  Receipt,
  ShoppingCart,
  Sparkles,
  Tags,
  Wallet,
} from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  fetchCustomer360,
  fetchCustomer360Summary,
  type Customer360Data,
  type SummaryStatus,
  type RiskSignal,
  type CustomerAction,
  type ComplaintRecord,
  type InteractionRecord,
  type TransactionRecord,
  type DevRequestRecord,
  type OfferRecord,
  type CollectionRecord,
  type MarketSignalRecord,
} from "@/lib/api";
import { formatCurrency, formatNumber, formatDate, cn } from "@/lib/utils";
import { ExpandableSection } from "@/components/expandable";

const riskTone: Record<string, string> = {
  زیاد: "bg-red-500",
  متوسط: "bg-amber-500",
  کم: "bg-emerald-500",
};

const riskText: Record<string, string> = {
  زیاد: "text-red-600 dark:text-red-400",
  متوسط: "text-amber-600 dark:text-amber-400",
  کم: "text-emerald-600 dark:text-emerald-400",
};

const severityTone: Record<string, string> = {
  زیاد: "bg-red-500",
  متوسط: "bg-amber-500",
  کم: "bg-emerald-500",
};

const statusTone: Record<string, string> = {
  "بسته‌شده": "bg-emerald-500",
  "انجام‌شده": "bg-emerald-500",
  "درحال بررسی": "bg-amber-500",
  "درحال توسعه": "bg-amber-500",
  "درحال مذاکره": "bg-amber-500",
};

const LOADER_TEXTS = [
  "در حال تحلیل داده‌های مشتری…",
  "در حال بررسی شکایات و تعاملات…",
  "در حال بررسی وضعیت خرید و پرداخت‌ها…",
  "در حال آماده‌سازی پیشنهادها…",
  "کمی صبر کنید؛ خلاصه در حال آماده شدن است…",
];

/* ------------------------------------------------------------------ pieces */

function SignalRow({ signal }: { signal: RiskSignal }) {
  return (
    <div className="flex items-start gap-2">
      <span className={cn("mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full", riskTone[signal.tone] ?? "bg-amber-500")} />
      <div className="min-w-0 leading-tight">
        <p className="text-xs font-medium">{signal.label}</p>
        <p className="text-xs text-muted-foreground">{signal.detail}</p>
        {signal.reasons && signal.reasons.length > 0 && (
          <p className="mt-0.5 text-[11px] text-muted-foreground/80">{"- " + signal.reasons.join("؛ ")}</p>
        )}
      </div>
    </div>
  );
}

function ActionItem({ action }: { action: CustomerAction }) {
  return (
    <div className="flex items-start gap-2 rounded-lg border bg-muted/30 p-2.5">
      <Lightbulb className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-500" />
      <div className="min-w-0 leading-tight">
        <p className="text-xs font-medium">{action.name}</p>
        <p className="mt-0.5 text-[11px] text-muted-foreground">{action.reason}</p>
        {action.next_step && (
          <p className="mt-0.5 text-[11px] text-muted-foreground/80">{action.next_step}</p>
        )}
      </div>
    </div>
  );
}

function MetaRow({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <span className="text-muted-foreground">{label}</span>
      <span className="truncate font-medium tabular-nums">{value}</span>
    </div>
  );
}

function ListBody<T>({
  items,
  render,
  previewCount = 2,
  empty,
}: {
  items: T[];
  render: (item: T) => ReactNode;
  previewCount?: number;
  empty: string;
}) {
  if (items.length === 0) {
    return <p className="text-xs text-muted-foreground">{empty}</p>;
  }
  return (
    <div className="space-y-2">
      {items.slice(0, previewCount).map((item, i) => (
        <div key={i}>{render(item)}</div>
      ))}
    </div>
  );
}

function FullList<T>({
  items,
  render,
  empty,
}: {
  items: T[];
  render: (item: T) => ReactNode;
  empty: string;
}) {
  if (items.length === 0) {
    return <p className="text-xs text-muted-foreground">{empty}</p>;
  }
  return (
    <div className="max-h-80 space-y-2 overflow-y-auto scrollbar-thin">
      {items.map((item, i) => (
        <div key={i}>{render(item)}</div>
      ))}
    </div>
  );
}

/* complaint ------------------------------------------------------------ */
function ComplaintCard({ c }: { c: ComplaintRecord }) {
  return (
    <div className="rounded-lg border bg-muted/30 p-2.5">
      <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
        <p className="text-xs font-medium">{c.title ?? "شکایت"}</p>
        {c.severity && (
          <span className="inline-flex items-center gap-1 text-[10px] text-muted-foreground">
            <span className={cn("h-1.5 w-1.5 rounded-full", severityTone[c.severity] ?? "bg-muted-foreground")} />
            شدت {c.severity}
          </span>
        )}
        {c.status && (
          <Badge
            variant="outline"
            className="gap-1 border-transparent text-[10px]"
          >
            <span className={cn("h-1.5 w-1.5 rounded-full", statusTone[c.status] ?? "bg-muted-foreground")} />
            {c.status}
          </Badge>
        )}
      </div>
      {c.text && <p className="mt-1 text-[11px] leading-relaxed text-muted-foreground">{c.text}</p>}
      <p className="mt-1 flex items-center gap-1 text-[10px] text-muted-foreground/80">
        <CalendarClock className="h-3 w-3" />
        {formatDate(c.date)}
        {c.product && <span>{" · "}{c.product}</span>}
      </p>
    </div>
  );
}

/* interaction ---------------------------------------------------------- */
function InteractionCard({ i }: { i: InteractionRecord }) {
  return (
    <div className="rounded-lg border bg-muted/30 p-2.5">
      <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
        <p className="text-xs font-medium">{i.type ?? "تعامل"}</p>
        {i.next_action && (
          <Badge variant="outline" className="gap-1 border-transparent text-[10px]">
            <Handshake className="h-3 w-3" />
            {i.next_action}
          </Badge>
        )}
      </div>
      {i.summary && <p className="mt-1 text-[11px] leading-relaxed text-muted-foreground">{i.summary}</p>}
      <p className="mt-1 flex items-center gap-1 text-[10px] text-muted-foreground/80">
        <CalendarClock className="h-3 w-3" />
        {formatDate(i.date)}
        {i.rep && <span>{" · نماینده: "}{i.rep}</span>}
      </p>
    </div>
  );
}

/* transaction ---------------------------------------------------------- */
function TransactionRow({ t }: { t: TransactionRecord }) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-lg border bg-muted/30 px-2.5 py-2">
      <div className="min-w-0 leading-tight">
        <p className="text-xs font-medium">{t.invoice}</p>
        <p className="text-[10px] text-muted-foreground">
          {formatDate(t.date)} · {formatNumber(t.lines)} قلم
        </p>
      </div>
      <span className="shrink-0 text-xs font-medium tabular-nums">{formatCurrency(t.amount)}</span>
    </div>
  );
}

/* dev request ---------------------------------------------------------- */
function DevCard({ d }: { d: DevRequestRecord }) {
  return (
    <div className="rounded-lg border bg-muted/30 p-2.5">
      <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
        <p className="text-xs font-medium">{d.type ?? "درخواست توسعه"}</p>
        {d.status && (
          <Badge variant="outline" className="gap-1 border-transparent text-[10px]">
            <span className={cn("h-1.5 w-1.5 rounded-full", statusTone[d.status] ?? "bg-muted-foreground")} />
            {d.status}
          </Badge>
        )}
      </div>
      {d.text && <p className="mt-1 text-[11px] leading-relaxed text-muted-foreground">{d.text}</p>}
      <p className="mt-1 flex items-center gap-1 text-[10px] text-muted-foreground/80">
        <CalendarClock className="h-3 w-3" />
        {formatDate(d.date)}
        {d.owner && <span>{" · "}{d.owner}</span>}
      </p>
    </div>
  );
}

/* offer ---------------------------------------------------------------- */
function OfferCard({ o }: { o: OfferRecord }) {
  const accepted = o.result === "قبول";
  const rejected = o.result === "رد شده" || o.result === "منقضی‌شده";
  return (
    <div className="flex items-center justify-between gap-3 rounded-lg border bg-muted/30 px-2.5 py-2">
      <div className="min-w-0 leading-tight">
        <p className="text-xs font-medium">{o.type ?? "پیشنهاد"}</p>
        <p className="text-[10px] text-muted-foreground">
          {formatDate(o.date)}
          {o.discount_pct != null && (
            <span>{" · تخفیف "}{formatNumber(Math.round(o.discount_pct * 100))}٪</span>
          )}
        </p>
      </div>
      <Badge
        variant="outline"
        className={cn(
          "shrink-0 border-transparent text-[10px]",
          accepted && "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400",
          rejected && "bg-muted text-muted-foreground",
          !accepted && !rejected && "bg-amber-500/10 text-amber-600 dark:text-amber-400"
        )}
      >
        {o.result ?? "نامشخص"}
      </Badge>
    </div>
  );
}

/* collection ----------------------------------------------------------- */
function CollectionRow({ c }: { c: CollectionRecord }) {
  const delayed = (c.delay_days ?? 0) > 0;
  const bounced = c.bounced === "بله";
  return (
    <div className="flex items-center justify-between gap-3 rounded-lg border bg-muted/30 px-2.5 py-2">
      <div className="min-w-0 leading-tight">
        <p className="text-xs font-medium">{formatDate(c.date)}</p>
        <p className="text-[10px] text-muted-foreground">
          {delayed ? `${formatNumber(c.delay_days ?? 0)} روز تأخیر` : "به‌موقع"}
          {bounced && <span className="text-red-500"> · چک برگشتی</span>}
        </p>
      </div>
      <span className="shrink-0 text-xs font-medium tabular-nums">{formatCurrency(c.amount)}</span>
    </div>
  );
}

/* market signal -------------------------------------------------------- */
function MarketCard({ m }: { m: MarketSignalRecord }) {
  return (
    <div className="rounded-lg border bg-muted/30 p-2.5">
      <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
        <p className="text-xs font-medium">{m.market ?? "بازار"}</p>
        {m.demand && (
          <Badge variant="outline" className="gap-1 border-transparent text-[10px]">
            تقاضا: {m.demand}
          </Badge>
        )}
        {m.trend && <Badge variant="outline" className="gap-1 border-transparent text-[10px]">روند: {m.trend}</Badge>}
      </div>
      {m.customer_signal && (
        <p className="mt-1 text-[11px] leading-relaxed text-muted-foreground">{m.customer_signal}</p>
      )}
      <p className="mt-1 flex items-center gap-1 text-[10px] text-muted-foreground/80">
        <CalendarClock className="h-3 w-3" />
        {formatDate(m.date)}
        {m.competitor && <span>{" · رقیب: "}{m.competitor}</span>}
      </p>
    </div>
  );
}

/* summary renderer ----------------------------------------------------- */
function SummaryText({ text }: { text: string }) {
  const lines = text.split("\n").filter((l) => l.trim() !== "");
  return (
    <div className="space-y-2">
      {lines.map((line, i) => {
        const trimmed = line.trim();
        if (trimmed.startsWith("- ") || trimmed.startsWith("• ")) {
          return (
            <p key={i} className="flex items-start gap-1.5 text-sm leading-relaxed text-foreground/90">
              <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-primary/70" />
              <span>{trimmed.replace(/^[-•]\s*/, "")}</span>
            </p>
          );
        }
        const isHeader = /^[^\s:]{2,}:$/.test(trimmed) || trimmed.startsWith("**");
        if (isHeader) {
          return (
            <p key={i} className="pt-1 text-sm font-semibold">
              {trimmed.replace(/\*\*/g, "")}
            </p>
          );
        }
        return (
          <p key={i} className="text-sm leading-relaxed text-foreground/90">
            {trimmed.replace(/\*\*/g, "")}
          </p>
        );
      })}
    </div>
  );
}

/* loader --------------------------------------------------------------- */
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

/* main ------------------------------------------------------------------ */
export function Customer360({ customerId, onBack }: { customerId: string; onBack: () => void }) {
  const [view, setView] = useState<Customer360Data | null>(null);
  const [error, setError] = useState(false);
  const [summary, setSummary] = useState<SummaryStatus | null>(null);
  const topRef = useRef<HTMLDivElement>(null);
  const stopPollRef = useRef<() => void>(() => {});

  useEffect(() => {
    topRef.current?.scrollIntoView({ block: "start" });
    setView(null);
    setSummary(null);
    stopPollRef.current();
    stopPollRef.current = () => {};

    fetchCustomer360(customerId)
      .then((data) => {
        setView(data);
        if (data.summaryReady) {
          setSummary({ status: "ready", summary: data.summary ?? "", generated: false });
          return;
        }
        let stopped = false;
        stopPollRef.current = () => {
          stopped = true;
        };
        let tries = 0;
        const tick = async () => {
          if (stopped) return;
          if (tries > 200) {
            setPollExhausted(true);
            return;
          }
          tries += 1;
          try {
            const res = await fetchCustomer360Summary(customerId);
            if (res.status === "ready") {
              setSummary(res);
              return;
            }
          } catch {
            /* keep polling */
          }
          setTimeout(tick, 2500);
        };
        tick();
      })
      .catch(() => setError(true));
    return () => stopPollRef.current();
  }, [customerId]);

  // Manual retry when automatic polling gave up (very long LLM latency).
  const [pollExhausted, setPollExhausted] = useState(false);
  useEffect(() => {
    setPollExhausted(false);
  }, [customerId]);

  function retrySummary() {
    setPollExhausted(false);
    let stopped = false;
    stopPollRef.current();
    stopPollRef.current = () => {
      stopped = true;
    };
    let tries = 0;
    const tick = async () => {
      if (stopped) return;
      if (tries > 200) {
        setPollExhausted(true);
        return;
      }
      tries += 1;
      try {
        const res = await fetchCustomer360Summary(customerId);
        if (res.status === "ready") {
          setSummary(res);
          return;
        }
      } catch {
        /* keep polling */
      }
      setTimeout(tick, 2500);
    };
    tick();
  }

  if (error) {
    return (
      <div className="flex h-full items-center justify-center pt-20">
        <p className="text-sm text-muted-foreground">امکان بارگذاری داده‌های مشتری وجود ندارد.</p>
      </div>
    );
  }

  if (!view) {
    return (
      <div className="space-y-4">
        <div className="h-16 animate-pulse rounded-xl border bg-muted/50" />
        <div className="h-64 animate-pulse rounded-xl border bg-muted/50" />
      </div>
    );
  }

  const barColor = riskTone[view.riskLevel] ?? "bg-amber-500";
  const summaryText = summary?.status === "ready" ? summary.summary : null;

  const stateChips: { key: string; label: string }[] = [
    { key: "relationship_health", label: "رابطه" },
    { key: "growth_opportunity", label: "رشد" },
    { key: "payment_risk", label: "پرداخت" },
    { key: "profitability", label: "سودآوری" },
    { key: "value", label: "ارزش" },
  ];
  // Statuses arrive already translated to Persian; only tone needs mapping.
  const stateTone: Record<string, string> = {
    "ضعیف": "bg-red-500",
    "بحرانی": "bg-red-500",
    "هشدار": "bg-amber-500",
    "رو به کاهش": "bg-amber-500",
    "سالم": "bg-emerald-500",
    "بالا": "bg-emerald-500",
    "مثبت": "bg-emerald-500",
    "در حال بهبود": "bg-emerald-500",
    "پایدار": "bg-emerald-500",
  };

  return (
    <div ref={topRef} className="space-y-4 animate-fade-in-up">
      {/* Header */}
      <div className="flex flex-wrap items-center gap-3 pt-4">
        <Button variant="ghost" size="icon" onClick={onBack} aria-label="بازگشت به مشتریان" className="shrink-0">
          <ArrowRight className="h-4 w-4" />
        </Button>
        <div className="min-w-0">
          <h1 className="truncate text-xl font-semibold tabular-nums tracking-tight">{customerId}</h1>
          <p className="truncate text-sm text-muted-foreground">نمای ۳۶۰ درجه مشتری</p>
        </div>
        <div className="mr-auto flex flex-wrap items-center gap-2">
          {String(view.customer["Customer_Segment"] ?? "") && (
            <Badge variant="outline">{String(view.customer["Customer_Segment"])}</Badge>
          )}
          {String(view.customer["Customer_Status"] ?? "") && (
            <Badge variant="outline">{String(view.customer["Customer_Status"])}</Badge>
          )}
          <Badge
            variant="outline"
            className={cn(
              "gap-1.5 border-transparent",
              view.riskLevel === "زیاد" && "bg-red-500/10",
              view.riskLevel === "متوسط" && "bg-amber-500/10",
              view.riskLevel === "کم" && "bg-emerald-500/10"
            )}
          >
            <span className={cn("h-1.5 w-1.5 rounded-full", barColor)} />
            <span className={riskText[view.riskLevel] ?? ""}>ریسک {view.riskLevel}</span>
          </Badge>
        </div>
      </div>

      {/* Intelligence summary (LLM) */}
      <Card className="border-primary/30 bg-gradient-to-br from-primary/5 to-transparent">
        <CardHeader className="pb-2">
          <div className="flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-primary" />
            <CardTitle className="text-sm">خلاصه هوشمند</CardTitle>
            {summaryText && (
              <Badge variant="outline" className="mr-auto gap-1 border-transparent bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
                <BadgeCheck className="h-3 w-3" />
                آماده
              </Badge>
            )}
          </div>
        </CardHeader>
        <CardContent>
          {summaryText ? (
            <SummaryText text={summaryText} />
          ) : pollExhausted ? (
            <div className="flex flex-col items-start gap-3">
              <p className="text-sm text-muted-foreground">
                آماده‌سازی خلاصه بیشتر از حد انتظار طول کشید. دوباره تلاش کنید.
              </p>
              <Button size="sm" onClick={retrySummary}>
                <Loader2 className="mr-1 h-3.5 w-3.5" />
                تلاش دوباره
              </Button>
            </div>
          ) : (
            <SummaryLoader />
          )}
        </CardContent>
      </Card>

      {/* Risk / Sales / Complaints */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <Card className="h-full">
          <CardHeader className="pb-2">
            <div className="flex items-center gap-2">
              <Activity className="h-4 w-4 text-muted-foreground" />
              <CardTitle className="text-sm">وضعیت مشتری</CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            <div className="flex items-end gap-1">
              <span className="text-4xl font-semibold">{view.riskLevel}</span>
            </div>
            {view.riskScore != null && (
              <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-muted">
                <div className={cn("h-full rounded-full", barColor)} style={{ width: `${view.riskScore}%` }} />
              </div>
            )}
            {stateChips
              .filter((c) => view.state[c.key] && view.state[c.key].status)
              .map((c) => {
                const st = view.state[c.key];
                const tone = stateTone[st.status] ?? "bg-muted-foreground";
                return (
                  <span key={c.key} className="mt-2 inline-flex items-center gap-1 rounded-full bg-muted px-2 py-0.5 text-[10px] text-muted-foreground">
                    <span className={cn("h-1.5 w-1.5 rounded-full", tone)} />
                    {c.label}: {st.status}
                  </span>
                );
              })}
            <div className="mt-4 space-y-3 border-t pt-4">
              {view.riskSignals.slice(0, 3).map((s) => (
                <SignalRow key={s.label + s.detail} signal={s} />
              ))}
            </div>
          </CardContent>
        </Card>

        <Card className="h-full">
          <CardHeader className="pb-2">
            <div className="flex items-center gap-2">
              <ShoppingCart className="h-4 w-4 text-muted-foreground" />
              <CardTitle className="text-sm">نمای فروش</CardTitle>
            </div>
          </CardHeader>
          <CardContent className="space-y-2.5">
            <MetaRow label="درآمد کل" value={formatCurrency(view.revenue)} />
            <MetaRow label="سفارش‌ها" value={formatNumber(view.orders)} />
            <MetaRow label="میانگین هر سفارش" value={formatCurrency(view.avgOrderValue)} />
            <MetaRow label="آخرین خرید" value={formatDate(view.lastPurchase)} />
            <MetaRow label="محصول اصلی" value={view.topProduct ?? "—"} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <div className="flex items-center gap-2">
              <MessageSquareWarning className="h-4 w-4 text-muted-foreground" />
              <CardTitle className="text-sm">شکایات</CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-6">
              <div>
                <span className="text-3xl font-semibold tabular-nums">{formatNumber(view.complaints)}</span>
                <p className="text-xs text-muted-foreground">کل شکایات</p>
              </div>
              <div>
                <span className="text-3xl font-semibold tabular-nums">{formatNumber(view.unresolvedComplaints)}</span>
                <p className="text-xs text-muted-foreground">در حال پیگیری</p>
              </div>
              <div>
                <span className="text-3xl font-semibold tabular-nums">{formatNumber(view.collectionsCount)}</span>
                <p className="text-xs text-muted-foreground">رویداد وصول</p>
              </div>
            </div>
            {view.complaintReasons.length > 0 ? (
              <ul className="mt-4 space-y-2 border-t pt-4">
                {view.complaintReasons.map((r) => (
                  <li key={r.reason} className="flex items-center justify-between text-xs">
                    <span className="text-muted-foreground">{r.reason}</span>
                    <span className="font-medium tabular-nums">{formatNumber(r.count)}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="mt-4 border-t pt-4 text-xs text-muted-foreground">
                در این بازه شکایتی ثبت نشده است.
              </p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Sections — varied responsive widths (dashboard/analyses style) */}
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-12">
        <div className="xl:col-span-5">
          <ExpandableSection
            className="h-full"
            icon={Activity}
            title="نشانه‌های وضعیت مشتری"
            count={view.riskSignals.length}
            preview={<div className="space-y-3">{view.riskSignals.slice(0, 3).map((s) => <SignalRow key={s.label + s.detail} signal={s} />)}</div>}
            full={<div className="max-h-80 space-y-3 overflow-y-auto scrollbar-thin">{view.riskSignals.map((s) => <SignalRow key={s.label + s.detail} signal={s} />)}</div>}
          />
        </div>

        <div className="xl:col-span-7">
          <ExpandableSection
            className="h-full"
            icon={Lightbulb}
            title="اقدام پیشنهادی"
            count={view.actions.length}
            preview={<div className="space-y-2">{view.actions.slice(0, 2).map((a) => <ActionItem key={a.id} action={a} />)}</div>}
            full={<div className="space-y-2">{view.actions.map((a) => <ActionItem key={a.id} action={a} />)}</div>}
          />
        </div>

        <div className="xl:col-span-7">
          <ExpandableSection
            className="h-full"
            icon={MessageSquareWarning}
            title="شکایات و عوامل آن"
            count={view.complaintList.length}
            preview={<ListBody items={view.complaintList} render={(c) => <ComplaintCard c={c} />} empty="شکایتی ثبت نشده است." />}
            full={<FullList items={view.complaintList} render={(c) => <ComplaintCard c={c} />} empty="شکایتی ثبت نشده است." />}
          />
        </div>

        <div className="xl:col-span-5">
          <ExpandableSection
            className="h-full"
            icon={Handshake}
            title="تعاملات و پیگیری‌ها"
            count={view.interactionsCount}
            preview={<ListBody items={view.interactions} render={(i) => <InteractionCard i={i} />} empty="تعاملی ثبت نشده است." />}
            full={<FullList items={view.interactions} render={(i) => <InteractionCard i={i} />} empty="تعاملی ثبت نشده است." />}
          />
        </div>

        <div className="xl:col-span-7">
          <ExpandableSection
            className="h-full"
            icon={Receipt}
            title="سفارش‌ها و تراکنش‌ها"
            count={view.transactions.length}
            preview={<ListBody items={view.transactions} render={(t) => <TransactionRow t={t} />} empty="تراکنشی ثبت نشده است." />}
            full={<FullList items={view.transactions} render={(t) => <TransactionRow t={t} />} empty="تراکنشی ثبت نشده است." />}
          />
        </div>

        <div className="xl:col-span-5">
          <ExpandableSection
            className="h-full"
            icon={ClipboardList}
            title="درخواست‌های توسعه محصول"
            count={view.devCount}
            badge={
              view.devOpen > 0 ? (
                <Badge variant="outline" className="gap-1 border-transparent bg-amber-500/10 text-amber-600 dark:text-amber-400">
                  {formatNumber(view.devOpen)} باز
                </Badge>
              ) : undefined
            }
            preview={<ListBody items={view.devRequests} render={(d) => <DevCard d={d} />} empty="درخواست توسعه‌ای ثبت نشده است." />}
            full={<FullList items={view.devRequests} render={(d) => <DevCard d={d} />} empty="درخواست توسعه‌ای ثبت نشده است." />}
          />
        </div>

        <div className="xl:col-span-5">
          <ExpandableSection
            className="h-full"
            icon={Tags}
            title="پیشنهادهای قیمتی"
            count={view.offers.length}
            badge={
              view.offerAcceptance != null ? (
                <Badge variant="outline" className="gap-1 border-transparent bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
                  پذیرش {formatNumber(Math.round(view.offerAcceptance * 100))}٪
                </Badge>
              ) : undefined
            }
            preview={<ListBody items={view.offers} render={(o) => <OfferCard o={o} />} empty="پیشنهادی ثبت نشده است." />}
            full={<FullList items={view.offers} render={(o) => <OfferCard o={o} />} empty="پیشنهادی ثبت نشده است." />}
          />
        </div>

        <div className="xl:col-span-7">
          <ExpandableSection
            className="h-full"
            icon={Wallet}
            title="وصول و پرداخت‌ها"
            count={view.collectionsCount}
            badge={
              view.bouncedChecks > 0 ? (
                <Badge variant="outline" className="gap-1 border-transparent bg-red-500/10 text-red-600 dark:text-red-400">
                  {formatNumber(view.bouncedChecks)} چک برگشتی
                </Badge>
              ) : undefined
            }
            preview={<ListBody items={view.collections} render={(c) => <CollectionRow c={c} />} empty="رویداد وصولی ثبت نشده است." />}
            full={<FullList items={view.collections} render={(c) => <CollectionRow c={c} />} empty="رویداد وصولی ثبت نشده است." />}
          />
        </div>

        {view.marketSignals.length > 0 && (
          <div className="xl:col-span-5">
            <ExpandableSection
              className="h-full"
              icon={MailQuestion}
              title="نشانه‌های بازار"
              count={view.marketSignals.length}
              preview={<ListBody items={view.marketSignals} render={(m) => <MarketCard m={m} />} empty="نشانه‌ای ثبت نشده است." />}
              full={<FullList items={view.marketSignals} render={(m) => <MarketCard m={m} />} empty="نشانه‌ای ثبت نشده است." />}
            />
          </div>
        )}

        <div className="xl:col-span-7">
          <ExpandableSection
            className="h-full"
            icon={FileText}
            title="مشخصات مشتری"
            alwaysExpandable
            preview={
              <div className="space-y-2.5">
                <MetaRow label="بخش بازار" value={String(view.customer["Customer_Segment"] ?? "—")} />
                <MetaRow label="وضعیت" value={String(view.customer["Customer_Status"] ?? "—")} />
                <MetaRow label="نماینده فروش" value={String(view.customer["Sales_Rep_ID"] ?? "—")} />
                <MetaRow label="شروع همکاری" value={formatDate(String(view.customer["Relationship_Start_Date"] ?? ""))} />
              </div>
            }
            full={
              <div className="max-h-96 space-y-2.5 overflow-y-auto scrollbar-thin">
                {Object.entries(view.customer).map(([k, v]) => (
                  <MetaRow key={k} label={k} value={v == null ? "—" : String(v)} />
                ))}
              </div>
            }
          />
        </div>
      </div>
    </div>
  );
}
