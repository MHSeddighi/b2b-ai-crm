import { useEffect, useState } from "react";
import {
  Users,
  MessageSquareWarning,
  DollarSign,
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
import { fetchDashboard, type DashboardData, type KpiValue } from "@/lib/api";
import { formatCompact } from "@/lib/utils";

const kpiIcons: Record<string, typeof Users> = {
  "کل مشتریان": Users,
  "درآمد کل": DollarSign,
  "سفارش‌ها": Users,
  "شکایات": MessageSquareWarning,
};

const pieColors = ["#6366f1", "#8b5cf6", "#10b981", "#f59e0b", "#ef4444", "#06b6d4"];

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
          <p className="text-2xl font-semibold tabular-nums tracking-tight">
            {formatCompact(kpi.value)}
          </p>
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

function PurchaseTrendChart({ data }: { data: DashboardData["purchaseTrend"] }) {
  return (
    <Card className="animate-fade-in-up" style={{ animationDelay: "240ms" }}>
      <CardHeader>
        <CardTitle className="text-base">روند فروش</CardTitle>
        <CardDescription>حجم فروش ماهانه (مبالغ کل)</CardDescription>
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
              <XAxis
                dataKey="month"
                tickLine={false}
                axisLine={false}
                tick={{ fontSize: 10 }}
                interval="preserveStartEnd"
                className="text-muted-foreground"
              />
              <YAxis
                tickLine={false}
                axisLine={false}
                tick={{ fontSize: 10 }}
                className="text-muted-foreground"
                tickFormatter={(v) => formatCompact(Number(v))}
              />
              <Tooltip
                contentStyle={{ borderRadius: 8, border: "1px solid hsl(var(--border))", fontSize: 12 }}
                formatter={(v) => [formatCompact(Number(v)), "مبلغ کل"]}
              />
              <Area
                type="monotone"
                dataKey="value"
                stroke="var(--chart-primary)"
                strokeWidth={2}
                fill="url(#purchaseGrad)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}

function ComplaintTrendChart({ data }: { data: DashboardData["complaintTrend"] }) {
  return (
    <Card className="animate-fade-in-up" style={{ animationDelay: "300ms" }}>
      <CardHeader>
        <CardTitle className="text-base">روند شکایات</CardTitle>
        <CardDescription>شکایات ثبت‌شده در هر ماه</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data} margin={{ top: 4, right: 4, left: -24, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-border" vertical={false} />
              <XAxis
                dataKey="month"
                tickLine={false}
                axisLine={false}
                tick={{ fontSize: 10 }}
                interval="preserveStartEnd"
                className="text-muted-foreground"
              />
              <YAxis
                tickLine={false}
                axisLine={false}
                tick={{ fontSize: 10 }}
                className="text-muted-foreground"
              />
              <Tooltip
                cursor={{ fill: "hsl(var(--muted))" }}
                contentStyle={{ borderRadius: 8, border: "1px solid hsl(var(--border))", fontSize: 12 }}
              />
              <Bar dataKey="value" radius={[4, 4, 0, 0]} fill="var(--chart-warning)" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}

function DistributionChart({
  title,
  subtitle,
  data,
}: {
  title: string;
  subtitle: string;
  data: DashboardData["segmentDistribution"];
}) {
  const total = data.reduce((acc, d) => acc + d.value, 0);
  return (
    <Card className="animate-fade-in-up" style={{ animationDelay: "360ms" }}>
      <CardHeader>
        <CardTitle className="text-base">{title}</CardTitle>
        <CardDescription>{subtitle}</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="flex items-center gap-6">
          <div className="h-48 w-48 shrink-0">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={data}
                  dataKey="value"
                  nameKey="name"
                  innerRadius={50}
                  outerRadius={80}
                  paddingAngle={2}
                >
                  {data.map((entry, i) => (
                    <Cell key={entry.name} fill={pieColors[i % pieColors.length]} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{ borderRadius: 8, border: "1px solid hsl(var(--border))", fontSize: 12 }}
                  formatter={(v) => [formatCompact(Number(v)), "تعداد"]}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="flex-1 space-y-3">
            {data.map((d, i) => (
              <div key={d.name} className="flex items-center justify-between text-sm">
                <span className="flex items-center gap-2 text-muted-foreground">
                  <span
                    className="h-2.5 w-2.5 rounded-full"
                    style={{ background: pieColors[i % pieColors.length] }}
                  />
                  {d.name}
                </span>
                <span className="font-medium tabular-nums">
                  {formatCompact(d.value)}
                  <span className="mr-1 text-xs text-muted-foreground">
                    {Math.round((d.value / (total || 1)) * 100)}٪
                  </span>
                </span>
              </div>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export function Dashboard() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchDashboard().then(setData).catch(() => setError("امکان بارگذاری داده‌ها وجود ندارد."));
  }, []);

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
          <p className="text-sm text-muted-foreground">
            نمای کلی عملکرد، فروش و وضعیت مشتریان کسب‌وکار.
          </p>
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

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-1 pt-4">
        <h1 className="text-2xl font-semibold tracking-tight">داشبورد</h1>
        <p className="text-sm text-muted-foreground">
          نمای کلی عملکرد، فروش و وضعیت مشتریان کسب‌وکار.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {data.kpis.map((kpi, i) => (
          <KpiCard key={kpi.label} kpi={kpi} index={i} />
        ))}
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <PurchaseTrendChart data={data.purchaseTrend} />
        <ComplaintTrendChart data={data.complaintTrend} />
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <DistributionChart
          title="توزیع سگمنت مشتریان"
          subtitle="تعداد مشتریان بر اساس سگمنت"
          data={data.segmentDistribution}
        />
        <DistributionChart
          title="وضعیت مشتریان"
          subtitle="تعداد مشتریان بر اساس وضعیت"
          data={data.statusDistribution}
        />
      </div>
    </div>
  );
}
