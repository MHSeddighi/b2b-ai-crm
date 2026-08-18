import { useEffect, useRef, type ReactNode } from "react";
import {
  Activity,
  AlertTriangle,
  ArrowLeft,
  Lightbulb,
  MessageSquareWarning,
  ShoppingCart,
  Sparkles,
} from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  getCustomer360,
  type Opportunity,
  type RiskSignal,
} from "@/lib/customer-intelligence";
import { riskColor } from "@/lib/mock-data";
import { formatCurrency, formatPercent, cn } from "@/lib/utils";
import type { Customer } from "@/lib/types";

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

function Stat({ label, value, valueClass }: { label: string; value: ReactNode; valueClass?: string }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <span className="text-muted-foreground">{label}</span>
      <span className={cn("truncate font-medium tabular-nums", valueClass)}>{value}</span>
    </div>
  );
}

function OpportunityRow({ opp }: { opp: Opportunity }) {
  const isUpsell = opp.type === "upsell";
  return (
    <div className="rounded-lg border bg-background p-3">
      <div className="flex items-center justify-between gap-2">
        <div className="flex min-w-0 items-center gap-2">
          <Badge variant={isUpsell ? "secondary" : "success"} className="shrink-0">
            {isUpsell ? "Upsell" : "Cross-sell"}
          </Badge>
          <span className="truncate text-sm font-medium">{opp.title}</span>
        </div>
        <span className="shrink-0 text-sm font-semibold tabular-nums">
          {opp.score}
          <span className="text-xs font-normal text-muted-foreground">/100</span>
        </span>
      </div>
      <p className="mt-1.5 text-xs text-muted-foreground">{opp.detail}</p>
    </div>
  );
}

export function Customer360({ customer, onBack }: { customer: Customer; onBack: () => void }) {
  const view = getCustomer360(customer);
  const risk = riskColor[customer.risk];
  const topRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    topRef.current?.scrollIntoView({ block: "start" });
  }, []);
  const initials = customer.name
    .split(" ")
    .map((p) => p[0])
    .slice(0, 2)
    .join("");
  const purchasePositive = customer.purchaseChange >= 0;

  return (
    <div ref={topRef} className="space-y-4 animate-fade-in-up">
      {/* Header */}
      <div className="flex flex-wrap items-center gap-3 pt-4">
        <Button
          variant="ghost"
          size="icon"
          onClick={onBack}
          aria-label="Back to customers"
          className="shrink-0"
        >
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <Avatar className="h-11 w-11 shrink-0">
          <AvatarFallback className="bg-primary/10 text-sm font-semibold text-primary">
            {initials}
          </AvatarFallback>
        </Avatar>
        <div className="min-w-0">
          <h1 className="truncate text-xl font-semibold tracking-tight">{customer.name}</h1>
          <p className="truncate text-sm text-muted-foreground">
            {customer.company} · {customer.segment} · {customer.region}
          </p>
        </div>
        <div className="ml-auto flex flex-wrap items-center gap-2">
          <Badge variant="outline" className={cn(risk.bg, "gap-1.5 border-transparent")}>
            <span className={cn("h-1.5 w-1.5 rounded-full", risk.dot)} />
            <span className={risk.text}>{risk.label} risk</span>
          </Badge>
          <span className="text-xs text-muted-foreground">
            Owner: <span className="text-foreground">{customer.accountOwner}</span>
          </span>
        </div>
      </div>

      {/* Intelligent summary */}
      <Card className="border-primary/30 bg-gradient-to-br from-primary/5 to-transparent">
        <CardHeader className="pb-2">
          <div className="flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-primary" />
            <CardTitle className="text-sm">Intelligent Summary</CardTitle>
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
              <AlertTriangle className="h-4 w-4 text-muted-foreground" />
              <CardTitle className="text-sm">Risk Score</CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            <div className="flex items-end gap-1">
              <span className="text-4xl font-semibold tabular-nums">{view.riskScore}</span>
              <span className="mb-1 text-sm text-muted-foreground">/ 100</span>
            </div>
            <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-muted">
              <div
                className={cn("h-full rounded-full", risk.dot)}
                style={{ width: `${view.riskScore}%` }}
              />
            </div>
            <p className={cn("mt-2 text-xs font-medium", risk.text)}>{risk.label} risk</p>
            <div className="mt-4 space-y-3 border-t pt-4">
              {view.riskSignals.map((s) => (
                <SignalRow key={s.label} signal={s} />
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <div className="flex items-center gap-2">
              <ShoppingCart className="h-4 w-4 text-muted-foreground" />
              <CardTitle className="text-sm">Sales Snapshot</CardTitle>
            </div>
          </CardHeader>
          <CardContent className="space-y-2.5">
            <Stat label="Revenue" value={formatCurrency(customer.revenue)} />
            <Stat label="Orders" value={view.orders} />
            <Stat label="Avg order value" value={formatCurrency(view.avgOrderValue)} />
            <Stat
              label="Purchase change"
              value={formatPercent(customer.purchaseChange)}
              valueClass={
                purchasePositive
                  ? "text-emerald-600 dark:text-emerald-400"
                  : "text-red-600 dark:text-red-400"
              }
            />
            <Stat label="Frequency" value={view.purchaseFrequency} />
            <Stat label="Top product" value={view.topProduct} />
            <Stat label="Last purchase" value={customer.lastPurchase} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <div className="flex items-center gap-2">
              <MessageSquareWarning className="h-4 w-4 text-muted-foreground" />
              <CardTitle className="text-sm">Complaints</CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-6">
              <div>
                <span className="text-3xl font-semibold tabular-nums">{customer.complaints}</span>
                <p className="text-xs text-muted-foreground">total</p>
              </div>
              <div>
                <span className="text-3xl font-semibold tabular-nums">{view.qualityComplaints}</span>
                <p className="text-xs text-muted-foreground">quality-related</p>
              </div>
            </div>
            {view.complaintReasons.length > 0 ? (
              <ul className="mt-4 space-y-2 border-t pt-4">
                {view.complaintReasons.map((r) => (
                  <li key={r.reason} className="flex items-center justify-between text-xs">
                    <span className="text-muted-foreground">{r.reason}</span>
                    <span className="font-medium tabular-nums">{r.count}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="mt-4 border-t pt-4 text-xs text-muted-foreground">
                No complaints in the current window.
              </p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Opportunities / Activity */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <Card>
          <CardHeader className="pb-2">
            <div className="flex items-center gap-2">
              <Lightbulb className="h-4 w-4 text-amber-500" />
              <CardTitle className="text-sm">Opportunities</CardTitle>
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            {view.opportunities.map((o) => (
              <OpportunityRow key={o.title} opp={o} />
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <div className="flex items-center gap-2">
              <Activity className="h-4 w-4 text-muted-foreground" />
              <CardTitle className="text-sm">Recent Activity</CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            <ol className="space-y-4 border-l pl-4">
              {view.activity.map((a) => (
                <li key={a.date + a.type} className="relative">
                  <span className="absolute -left-[22px] top-1 h-2 w-2 rounded-full bg-border" />
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-xs font-medium">{a.type}</span>
                    <span className="text-xs tabular-nums text-muted-foreground">{a.date}</span>
                  </div>
                  <p className="text-xs text-muted-foreground">{a.detail}</p>
                </li>
              ))}
            </ol>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
