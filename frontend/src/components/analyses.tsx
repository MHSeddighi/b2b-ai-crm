import { useEffect, useState } from "react";
import {
  AlertTriangle,
  ArrowLeftRight,
  FileText,
  MessageSquareWarning,
  Target,
  TrendingDown,
  TrendingUp,
} from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ExpandableSection } from "@/components/expandable";
import { fetchAnalyses, type AnalysesData, type IncomeRecommendation } from "@/lib/api";
import { formatCurrency, formatNumber, formatDate, cn } from "@/lib/utils";

const riskChip: Record<string, string> = {
  زیاد: "bg-red-500/10 text-red-600 dark:text-red-400",
  متوسط: "bg-amber-500/10 text-amber-600 dark:text-amber-400",
  کم: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400",
};

function RecommendationCard({ rec }: { rec: IncomeRecommendation }) {
  const icon =
    rec.tone === "positive" ? <TrendingUp className="h-4 w-4" /> : rec.tone === "warning" ? <AlertTriangle className="h-4 w-4" /> : <TrendingDown className="h-4 w-4" />;
  return (
    <div
      className={cn(
        "rounded-xl border p-4 transition-colors",
        rec.tone === "positive" && "border-emerald-500/30 bg-emerald-500/5",
        rec.tone === "warning" && "border-amber-500/30 bg-amber-500/5",
        rec.tone === "negative" && "border-red-500/30 bg-red-500/5"
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
        <div className="min-w-0 space-y-1">
          <p className="text-sm font-semibold leading-snug">{rec.title}</p>
          <p className="text-xs leading-relaxed text-muted-foreground">{rec.detail}</p>
        </div>
      </div>
    </div>
  );
}

function AtRiskTable({ rows, preview }: { rows: AnalysesData["atRisk"]; preview: boolean }) {
  const slice = preview ? rows.slice(0, 5) : rows;
  return (
    <div className="max-h-96 overflow-y-auto scrollbar-thin">
      <table className="w-full text-xs">
        <thead className="sticky top-0 bg-muted text-muted-foreground">
          <tr>
            <th className="px-2 py-2 text-right font-medium">مشتری</th>
            <th className="px-2 py-2 text-right font-medium">بخش</th>
            <th className="px-2 py-2 text-right font-medium">شکایت</th>
            <th className="px-2 py-2 text-right font-medium">سفارش</th>
            <th className="px-2 py-2 text-right font-medium">درآمد</th>
            <th className="px-2 py-2 text-right font-medium">آخرین خرید</th>
            <th className="px-2 py-2 text-right font-medium">وضعیت</th>
          </tr>
        </thead>
        <tbody>
          {slice.map((r) => (
            <tr key={r.customer} className="border-t">
              <td className="px-2 py-2 font-medium tabular-nums">{r.customer}</td>
              <td className="px-2 py-2 text-muted-foreground">{r.segment ?? "—"}</td>
              <td className="px-2 py-2 tabular-nums">{formatNumber(r.complaints)}</td>
              <td className="px-2 py-2 tabular-nums">{formatNumber(r.orders)}</td>
              <td className="px-2 py-2 font-medium tabular-nums">{formatCurrency(r.revenue)}</td>
              <td className="px-2 py-2 text-muted-foreground">
                {formatDate(r.last_purchase)}
                {r.days_since != null && (
                  <span className="mr-1 text-[10px]">({formatNumber(r.days_since)} روز)</span>
                )}
              </td>
              <td className="px-2 py-2">
                <span className={cn("inline-block rounded-md px-1.5 py-0.5 text-[10px]", riskChip[r.risk_level] ?? riskChip["متوسط"])}>
                  {r.risk_level}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function Analyses() {
  const [data, setData] = useState<AnalysesData | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    fetchAnalyses().then(setData).catch(() => setError(true));
  }, []);

  if (error) {
    return (
      <div className="flex h-full items-center justify-center pt-20">
        <p className="text-sm text-muted-foreground">امکان بارگذاری تحلیل‌ها وجود ندارد.</p>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="space-y-6">
        <div className="flex flex-col gap-1 pt-4">
          <h1 className="text-2xl font-semibold tracking-tight">تحلیل‌ها</h1>
          <p className="text-sm text-muted-foreground">تحلیل‌های محاسبه‌شده از داده‌های واقعی مشتریان؛ برای مشاهده نتایج روی هر بخش کلیک کنید.</p>
        </div>
        <div className="h-72 animate-pulse rounded-xl border bg-muted/50" />
        <div className="h-72 animate-pulse rounded-xl border bg-muted/50" />
      </div>
    );
  }

  const maxTheme = data.complaintThemes.length ? Math.max(...data.complaintThemes.map((t) => t.count)) : 1;
  const maxRevenue = data.revenueConcentration.length ? Math.max(...data.revenueConcentration.map((r) => r.value)) : 1;
  const cf = data.churnFactors;

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-1 pt-4">
        <h1 className="text-2xl font-semibold tracking-tight">تحلیل‌ها</h1>
        <p className="text-sm text-muted-foreground">
          تحلیل‌های محاسبه‌شده از داده‌های واقعی مشتریان؛ برای مشاهده نتایج روی هر بخش کلیک کنید.
        </p>
      </div>

      {/* Income recommendations */}
      <div>
        <div className="mb-3 flex items-center gap-2">
          <Target className="h-4 w-4 text-primary" />
          <h2 className="text-base font-semibold">پیشنهادها برای درآمد بهتر</h2>
        </div>
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          {data.incomeRecommendations.map((rec) => (
            <RecommendationCard key={rec.id} rec={rec} />
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-12">
        {/* At-risk accounts */}
        <div className="xl:col-span-7">
        <ExpandableSection
          className="h-full"
          icon={AlertTriangle}
          title="نمای کلی حساب‌های پرریسک"
          count={data.atRisk.length}
          badge={
            <Badge variant="outline" className="gap-1 border-transparent bg-red-500/10 text-red-600 dark:text-red-400">
              ریسک
            </Badge>
          }
          preview={<AtRiskTable rows={data.atRisk} preview />}
          full={<AtRiskTable rows={data.atRisk} preview={false} />}
        />

        </div>
        <div className="xl:col-span-5">
        <ExpandableSection
          className="h-full"
          icon={TrendingDown}
          title="عوامل ریزش"
          alwaysExpandable
          badge={
            <Badge variant="outline" className="gap-1 border-transparent bg-amber-500/10 text-amber-600 dark:text-amber-400">
              ریزش
            </Badge>
          }
          preview={
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              <div className="rounded-lg border bg-muted/30 p-3 text-center">
                <p className="text-xl font-semibold tabular-nums">{formatNumber(cf.inactive_over_365)}</p>
                <p className="mt-1 text-[11px] text-muted-foreground">بدون خرید +۱ سال</p>
              </div>
              <div className="rounded-lg border bg-muted/30 p-3 text-center">
                <p className="text-xl font-semibold tabular-nums">{formatNumber(cf.inactive_180_365)}</p>
                <p className="mt-1 text-[11px] text-muted-foreground">بدون خرید ۶ تا ۱۲ ماه</p>
              </div>
              <div className="rounded-lg border bg-muted/30 p-3 text-center">
                <p className="text-xl font-semibold tabular-nums">{formatNumber(cf.never_bought)}</p>
                <p className="mt-1 text-[11px] text-muted-foreground">بدون هیچ خریدی</p>
              </div>
              <div className="rounded-lg border bg-red-500/5 p-3 text-center">
                <p className="text-xl font-semibold tabular-nums">{formatNumber(cf.inactive_with_complaints)}</p>
                <p className="mt-1 text-[11px] text-muted-foreground">راکد + دارای شکایت</p>
              </div>
            </div>
          }
          full={
            <div className="space-y-3">
              <div className="rounded-lg border bg-muted/30 p-3 text-xs leading-relaxed text-muted-foreground">
                {formatNumber(cf.inactive_with_complaints)} مشتری که بیش از ۶ ماه خریدی نداشته‌اند، شکایت نیز ثبت کرده‌اند — این ترکیب قوی‌ترین نشانه‌ی از دست رفتن مشتری است. در مجموع {formatNumber(cf.inactive_over_365 + cf.inactive_180_365)} مشتری بیش از ۶ ماه است که خریدی نداشته‌اند.
              </div>
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                <div className="rounded-lg border bg-muted/30 p-3 text-center">
                  <p className="text-xl font-semibold tabular-nums">{formatNumber(cf.inactive_over_365)}</p>
                  <p className="mt-1 text-[11px] text-muted-foreground">بدون خرید +۱ سال</p>
                </div>
                <div className="rounded-lg border bg-muted/30 p-3 text-center">
                  <p className="text-xl font-semibold tabular-nums">{formatNumber(cf.inactive_180_365)}</p>
                  <p className="mt-1 text-[11px] text-muted-foreground">بدون خرید ۶ تا ۱۲ ماه</p>
                </div>
                <div className="rounded-lg border bg-muted/30 p-3 text-center">
                  <p className="text-xl font-semibold tabular-nums">{formatNumber(cf.never_bought)}</p>
                  <p className="mt-1 text-[11px] text-muted-foreground">بدون هیچ خریدی</p>
                </div>
                <div className="rounded-lg border bg-red-500/5 p-3 text-center">
                  <p className="text-xl font-semibold tabular-nums">{formatNumber(cf.inactive_with_complaints)}</p>
                  <p className="mt-1 text-[11px] text-muted-foreground">راکد + دارای شکایت</p>
                </div>
              </div>
            </div>
          }
        />

        </div>
        <div className="xl:col-span-5">
        <ExpandableSection
          className="h-full"
          icon={MessageSquareWarning}
          title="مضامین شکایات"
          count={data.complaintThemes.length}
          badge={
            <Badge variant="outline" className="gap-1 border-transparent bg-indigo-500/10 text-indigo-600 dark:text-indigo-400">
              شکایات
            </Badge>
          }
          preview={
            data.complaintThemes.length === 0 ? (
              <p className="rounded-lg border border-dashed p-4 text-center text-xs text-muted-foreground">شکایتی ثبت نشده است.</p>
            ) : (
            <div className="space-y-2">
              {data.complaintThemes.slice(0, 4).map((t) => (
                <div key={t.name} className="flex items-center gap-3">
                  <span className="w-36 truncate text-xs text-muted-foreground">{t.name}</span>
                  <div className="h-2 flex-1 overflow-hidden rounded-full bg-muted">
                    <div className="h-full rounded-full bg-indigo-500/70" style={{ width: `${(t.count / maxTheme) * 100}%` }} />
                  </div>
                  <span className="w-10 text-left text-xs font-medium tabular-nums">{formatNumber(t.count)}</span>
                </div>
              ))}
            </div>
            )
          }
          full={
            <div className="max-h-80 space-y-2 overflow-y-auto scrollbar-thin">
              {data.complaintThemes.map((t) => (
                <div key={t.name} className="flex items-center gap-3">
                  <span className="w-44 truncate text-xs text-muted-foreground">{t.name}</span>
                  <div className="h-2 flex-1 overflow-hidden rounded-full bg-muted">
                    <div className="h-full rounded-full bg-indigo-500/70" style={{ width: `${(t.count / maxTheme) * 100}%` }} />
                  </div>
                  <span className="w-10 text-left text-xs font-medium tabular-nums">{formatNumber(t.count)}</span>
                </div>
              ))}
            </div>
          }
        />

        </div>
        <div className="xl:col-span-7">
        <ExpandableSection
          className="h-full"
          icon={FileText}
          title="تمرکز درآمد"
          count={data.revenueConcentration.length}
          badge={
            <Badge variant="outline" className="gap-1 border-transparent bg-primary/10 text-primary">
              ریسک
            </Badge>
          }
          preview={
            data.revenueConcentration.length === 0 ? (
              <p className="rounded-lg border border-dashed p-4 text-center text-xs text-muted-foreground">داده‌ای موجود نیست.</p>
            ) : (
            <div className="space-y-2">
              {data.revenueConcentration.slice(0, 3).map((s) => (
                <div key={s.name} className="flex items-center gap-3">
                  <span className="w-16 truncate text-xs text-muted-foreground">{s.name}</span>
                  <div className="h-2 flex-1 overflow-hidden rounded-full bg-muted">
                    <div className="h-full rounded-full bg-primary/70" style={{ width: `${(s.value / maxRevenue) * 100}%` }} />
                  </div>
                  <span className="w-16 text-left text-xs font-medium tabular-nums">{formatCurrency(s.value)}</span>
                </div>
              ))}
            </div>
            )
          }
          full={
            <div className="max-h-80 space-y-2 overflow-y-auto scrollbar-thin">
              {data.revenueConcentration.map((s) => (
                <div key={s.name} className="flex items-center gap-3">
                  <span className="w-20 truncate text-xs text-muted-foreground">{s.name}</span>
                  <div className="h-2 flex-1 overflow-hidden rounded-full bg-muted">
                    <div className="h-full rounded-full bg-primary/70" style={{ width: `${(s.value / maxRevenue) * 100}%` }} />
                  </div>
                  <span className="w-16 text-left text-xs font-medium tabular-nums">{formatCurrency(s.value)}</span>
                  <span className="w-14 text-left text-[10px] text-muted-foreground">{formatNumber(s.customers)} مشتری</span>
                </div>
              ))}
            </div>
          }
        />
        </div>
      </div>

      {/* Note */}
      <Card className="animate-fade-in-up border-dashed">
        <CardHeader className="pb-2">
          <div className="flex items-center gap-2">
            <ArrowLeftRight className="h-4 w-4 text-muted-foreground" />
            <CardTitle className="text-sm">نکته</CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          <p className="text-xs leading-relaxed text-muted-foreground">
            همه‌ی این تحلیل‌ها به‌صورت خودکار از داده‌های واقعی سامانه محاسبه شده‌اند و هر بار که داده‌ها به‌روزرسانی شوند، دوباره محاسبه می‌شوند. برای بررسی جزئیات هر مشتری، به صفحه «مشتریان» بروید.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
