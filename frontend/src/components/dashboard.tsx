import {
  Users,
  AlertTriangle,
  MessageSquareWarning,
  DollarSign,
  ArrowUpRight,
  ArrowDownRight,
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
import {
  dashboardKpis,
  purchaseTrend,
  complaintTrend,
  riskTiers,
} from "@/lib/mock-data";
import { formatCompact } from "@/lib/utils";
import type { Kpi } from "@/lib/types";

const kpiIcons: Record<string, typeof Users> = {
  "Total Customers": Users,
  "Customers At Risk": AlertTriangle,
  Complaints: MessageSquareWarning,
  Revenue: DollarSign,
};

const riskColors: Record<string, string> = {
  Low: "#10b981",
  Medium: "#f59e0b",
  High: "#ef4444",
};

function KpiCard({ kpi, index }: { kpi: Kpi; index: number }) {
  const Icon = kpiIcons[kpi.label] ?? Users;
  const positive = kpi.trend === "up";
  const TrendIcon = positive ? ArrowUpRight : ArrowDownRight;
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
          <p className="text-2xl font-semibold tracking-tight">{kpi.value}</p>
          {kpi.change && (
            <span
              className={`inline-flex items-center gap-0.5 rounded-md px-1.5 py-0.5 text-xs font-medium ${
                positive
                  ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
                  : "bg-red-500/10 text-red-600 dark:text-red-400"
              }`}
            >
              <TrendIcon className="h-3 w-3" />
              {kpi.change}
            </span>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

function PurchaseTrendChart() {
  return (
    <Card className="animate-fade-in-up" style={{ animationDelay: "240ms" }}>
      <CardHeader>
        <CardTitle className="text-base">Purchase Trend</CardTitle>
        <CardDescription>Monthly purchase volume (in millions)</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={purchaseTrend} margin={{ top: 4, right: 4, left: -16, bottom: 0 }}>
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
                tick={{ fontSize: 12 }}
                className="text-muted-foreground"
              />
              <YAxis
                tickLine={false}
                axisLine={false}
                tick={{ fontSize: 12 }}
                className="text-muted-foreground"
                tickFormatter={(v) => `$${v}M`}
              />
              <Tooltip
                contentStyle={{ borderRadius: 8, border: "1px solid hsl(var(--border))", fontSize: 12 }}
                formatter={(v) => [`$${v}M`, "Volume"]}
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

function ComplaintTrendChart() {
  return (
    <Card className="animate-fade-in-up" style={{ animationDelay: "300ms" }}>
      <CardHeader>
        <CardTitle className="text-base">Complaint Trend</CardTitle>
        <CardDescription>Complaints logged per month</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={complaintTrend} margin={{ top: 4, right: 4, left: -24, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-border" vertical={false} />
              <XAxis
                dataKey="month"
                tickLine={false}
                axisLine={false}
                tick={{ fontSize: 12 }}
                className="text-muted-foreground"
              />
              <YAxis
                tickLine={false}
                axisLine={false}
                tick={{ fontSize: 12 }}
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

function CustomerRiskChart() {
  const total = riskTiers.reduce((acc, t) => acc + t.customers, 0);
  return (
    <Card className="animate-fade-in-up" style={{ animationDelay: "360ms" }}>
      <CardHeader>
        <CardTitle className="text-base">Customer Risk Distribution</CardTitle>
        <CardDescription>Count of customers by risk tier</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="flex items-center gap-6">
          <div className="h-48 w-48 shrink-0">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={riskTiers}
                  dataKey="customers"
                  nameKey="tier"
                  innerRadius={50}
                  outerRadius={80}
                  paddingAngle={2}
                >
                  {riskTiers.map((entry) => (
                    <Cell key={entry.tier} fill={riskColors[entry.tier]} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{ borderRadius: 8, border: "1px solid hsl(var(--border))", fontSize: 12 }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="flex-1 space-y-3">
            {riskTiers.map((tier) => (
              <div key={tier.tier} className="flex items-center justify-between text-sm">
                <span className="flex items-center gap-2 text-muted-foreground">
                  <span
                    className="h-2.5 w-2.5 rounded-full"
                    style={{ background: riskColors[tier.tier] }}
                  />
                  {tier.tier} risk
                </span>
                <span className="font-medium">
                  {tier.customers}
                  <span className="ml-1 text-xs text-muted-foreground">
                    {Math.round((tier.customers / total) * 100)}%
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
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {dashboardKpis.map((kpi, i) => (
          <KpiCard key={kpi.label} kpi={kpi} index={i} />
        ))}
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <PurchaseTrendChart />
        <ComplaintTrendChart />
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <CustomerRiskChart />
        <Card className="animate-fade-in-up" style={{ animationDelay: "420ms" }}>
          <CardHeader>
            <CardTitle className="text-base">Risk Revenue Exposure</CardTitle>
            <CardDescription>At-risk revenue by tier ($M)</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-48">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={riskTiers}
                  layout="vertical"
                  margin={{ top: 4, right: 8, left: 8, bottom: 0 }}
                >
                  <CartesianGrid strokeDasharray="3 3" className="stroke-border" horizontal={false} />
                  <XAxis type="number" hide className="text-muted-foreground" />
                  <YAxis
                    type="category"
                    dataKey="tier"
                    tickLine={false}
                    axisLine={false}
                    width={64}
                    tick={{ fontSize: 12 }}
                    className="text-muted-foreground"
                  />
                  <Tooltip
                    cursor={{ fill: "hsl(var(--muted))" }}
                    contentStyle={{ borderRadius: 8, border: "1px solid hsl(var(--border))", fontSize: 12 }}
                    formatter={(v) => [`$${formatCompact(Number(v))}`, "Revenue"]}
                  />
                  <Bar dataKey="revenue" radius={[0, 4, 4, 0]} barSize={18}>
                    {riskTiers.map((entry) => (
                      <Cell key={entry.tier} fill={riskColors[entry.tier]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
