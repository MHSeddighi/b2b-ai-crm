import { useEffect, useRef, useState } from "react";
import {
  Activity,
  ArrowRight,
  Lightbulb,
  MessageSquareWarning,
  ShoppingCart,
  Sparkles,
  Wallet,
} from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { fetchCustomer360, type Customer360Data, type RiskSignal } from "@/lib/api";
import { formatCurrency, formatNumber, cn } from "@/lib/utils";

function SignalRow({ signal }: { signal: RiskSignal }) {
  const tone =
    signal.tone === "positive"
      ? "bg-emerald-500"
      : signal.tone === "negative"
        ? "bg-red-500"
        : "bg-amber-500";
  return (
    <div className="flex items-start gap-2">
      <span className={cn("mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full", tone)} />
      <div className="min-w-0 leading-tight">
        <p className="text-xs font-medium">{signal.label}</p>
        <p className="text-xs text-muted-foreground">{signal.detail}</p>
      </div>
    </div>
  );
}

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

export function Customer360({ customerId, onBack }: { customerId: string; onBack: () => void }) {
  const [view, setView] = useState<Customer360Data | null>(null);
  const [error, setError] = useState(false);
  const topRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    topRef.current?.scrollIntoView({ block: "start" });
    fetchCustomer360(customerId)
      .then(setView)
      .catch(() => setError(true));
  }, [customerId]);

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

  return (
    <div ref={topRef} className="space-y-4 animate-fade-in-up">
      {/* Header */}
      <div className="flex flex-wrap items-center gap-3 pt-4">
        <Button
          variant="ghost"
          size="icon"
          onClick={onBack}
          aria-label="بازگشت به مشتریان"
          className="shrink-0"
        >
          <ArrowRight className="h-4 w-4" />
        </Button>
        <div className="min-w-0">
          <h1 className="truncate text-xl font-semibold tabular-nums tracking-tight">{customerId}</h1>
          <p className="truncate text-sm text-muted-foreground">نمای ۳۶۰ درجه مشتری</p>
        </div>
        <div className="mr-auto flex flex-wrap items-center gap-2">
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

      {/* Intelligent summary */}
      <Card className="border-primary/30 bg-gradient-to-br from-primary/5 to-transparent">
        <CardHeader className="pb-2">
          <div className="flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-primary" />
            <CardTitle className="text-sm">خلاصه هوشمند</CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          <p className="text-sm leading-relaxed text-foreground/90">{view.summary}</p>
        </CardContent>
      </Card>

      {/* Risk / Sales / Complaints */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="pb-2">
            <div className="flex items-center gap-2">
              <Activity className="h-4 w-4 text-muted-foreground" />
              <CardTitle className="text-sm">امتیاز ریسک</CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            <div className="flex items-end gap-1">
              <span className="text-4xl font-semibold tabular-nums">{formatNumber(view.riskScore)}</span>
              <span className="mb-1 text-sm text-muted-foreground">/ ۱۰۰</span>
            </div>
            <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-muted">
              <div
                className={cn("h-full rounded-full", barColor)}
                style={{ width: `${view.riskScore}%` }}
              />
            </div>
            <p className={cn("mt-2 text-xs font-medium", riskText[view.riskLevel])}>
              ریسک {view.riskLevel}
            </p>
            <div className="mt-4 space-y-3 border-t pt-4">
              {view.riskSignals.map((s) => (
                <SignalRow key={s.label + s.detail} signal={s} />
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <div className="flex items-center gap-2">
              <ShoppingCart className="h-4 w-4 text-muted-foreground" />
              <CardTitle className="text-sm">نمای فروش</CardTitle>
            </div>
          </CardHeader>
          <CardContent className="space-y-2.5">
            <div className="flex items-center justify-between gap-3">
              <span className="text-muted-foreground">درآمد کل</span>
              <span className="truncate font-medium tabular-nums">{formatCurrency(view.revenue)}</span>
            </div>
            <div className="flex items-center justify-between gap-3">
              <span className="text-muted-foreground">سفارش‌ها</span>
              <span className="truncate font-medium tabular-nums">{formatNumber(view.orders)}</span>
            </div>
            <div className="flex items-center justify-between gap-3">
              <span className="text-muted-foreground">میانگین هر سفارش</span>
              <span className="truncate font-medium tabular-nums">{formatCurrency(view.avgOrderValue)}</span>
            </div>
            <div className="flex items-center justify-between gap-3">
              <span className="text-muted-foreground">آخرین خرید</span>
              <span className="truncate font-medium tabular-nums">{view.lastPurchase ?? "—"}</span>
            </div>
            <div className="flex items-center justify-between gap-3">
              <span className="text-muted-foreground">محصول اصلی</span>
              <span className="truncate font-medium tabular-nums">{view.topProduct ?? "—"}</span>
            </div>
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
                <span className="text-3xl font-semibold tabular-nums">
                  {formatNumber(view.collectionsCount)}
                </span>
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

      {/* Collections / opportunity */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <Card>
          <CardHeader className="pb-2">
            <div className="flex items-center gap-2">
              <Wallet className="h-4 w-4 text-muted-foreground" />
              <CardTitle className="text-sm">وصول</CardTitle>
            </div>
          </CardHeader>
          <CardContent className="space-y-2.5">
            <div className="flex items-center justify-between gap-3">
              <span className="text-muted-foreground">مبلغ وصول‌شده</span>
              <span className="truncate font-medium tabular-nums">{formatCurrency(view.collectionsAmount)}</span>
            </div>
            <div className="flex items-center justify-between gap-3">
              <span className="text-muted-foreground">تعداد رویدادهای وصول</span>
              <span className="truncate font-medium tabular-nums">{formatNumber(view.collectionsCount)}</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <div className="flex items-center gap-2">
              <Lightbulb className="h-4 w-4 text-amber-500" />
              <CardTitle className="text-sm">اقدام پیشنهادی</CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            <p className="text-sm leading-relaxed text-muted-foreground">
              {view.riskLevel === "زیاد"
                ? `این مشتری در ریسک بالاست و نیاز به توجه دارد؛ شکایات و فاصله خرید را بررسی و با نماینده فروش (${String(view.customer["Sales_Rep_ID"] ?? "—")}) پیگیری کنید.`
                : view.riskLevel === "متوسط"
                  ? "مشتری وضعیت نسبتاً پایداری دارد اما نشانه‌های هشدار اولیه دیده می‌شود؛ روند شکایات و فاصله خرید را از نزدیک پایش کنید."
                  : "مشتری در وضعیت سالمی است و کاندید مناسبی برای توسعه و فروش بیشتر است."}
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
