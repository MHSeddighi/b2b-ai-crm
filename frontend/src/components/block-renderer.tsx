import { useMemo } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import ReactMarkdown from "react-markdown";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { formatNumber } from "@/lib/utils";
import {
  resolveChartData,
  resolveMetricValue,
  resolveTable,
  type Block,
  type ChartBlock,
  type CustomerCardBlock,
  type HistogramBlock,
  type MetricBlock,
  type OrderCardBlock,
  type ProductCardBlock,
  type RecommendationBlock,
  type SqlResult,
  type TableBlock,
} from "@/lib/blocks";

const chartColors = ["#6366f1", "#8b5cf6", "#10b981", "#f59e0b", "#ef4444", "#06b6d4"];

// Themed recharts tooltip — uses the app's CSS variables so the hover box
// follows the active light/dark theme instead of recharts' default white card.
function ChartTooltip({ active, payload, label }: {
  active?: boolean;
  payload?: { name?: string; dataKey?: string | number; value?: unknown; color?: string; fill?: string }[];
  label?: unknown;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg border bg-background px-3 py-2 text-xs shadow-lg">
      {label != null && label !== "" && (
        <p className="mb-1 font-semibold text-foreground">{String(label)}</p>
      )}
      <div className="space-y-0.5">
        {payload.map((p) => (
          <p key={String(p.dataKey ?? p.name)} className="flex items-center justify-start gap-2 text-muted-foreground">
            <span
              className="inline-block h-2.5 w-2.5 shrink-0 rounded-sm"
              style={{ background: p.color ?? p.fill ?? chartColors[0] }}
            />
            <span className="truncate">{p.name ?? p.dataKey}</span>
            <span className="font-semibold tabular-nums text-foreground">
              {typeof p.value === "number" ? formatNumber(p.value) : String(p.value)}
            </span>
          </p>
        ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Markdown
// ---------------------------------------------------------------------------
function MarkdownBlock({ content }: { content: string }) {
  return (
    <div className="prose-sm max-w-none text-sm leading-relaxed [&_table]:text-xs [&_table]:border [&_td]:border [&_th]:border [&_td]:px-2 [&_th]:px-2 [&_td]:py-1 [&_th]:py-1 [&_code]:rounded [&_code]:bg-muted [&_code]:px-1">
      <ReactMarkdown>{content}</ReactMarkdown>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Metric
// ---------------------------------------------------------------------------
function MetricBlockView({ block, results }: { block: MetricBlock; results: Record<string, SqlResult> }) {
  const value = useMemo(() => resolveMetricValue(block, results), [block, results]);
  const trend = block.trend;
  return (
    <div className="rounded-lg border bg-card p-3">
      <p className="text-[11px] text-muted-foreground">{block.label}</p>
      <p className="mt-0.5 text-2xl font-semibold tabular-nums">{value ?? "—"}</p>
      {trend && (
        <span
          className={
            "text-xs " +
            (trend === "up" ? "text-emerald-500" : trend === "down" ? "text-red-500" : "text-muted-foreground")
          }
        >
          {trend === "up" ? "↑" : trend === "down" ? "↓" : "•"} {block.change ?? ""}
        </span>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Chart
// ---------------------------------------------------------------------------
function ChartBlockView({ block, results }: { block: ChartBlock; results: Record<string, SqlResult> }) {
  const res = resolveChartData(block, results);
  if (!res || !res.rows.length) {
    return <p className="text-xs text-muted-foreground">داده‌ای برای نمودار موجود نیست.</p>;
  }
  const cols = res.columns;
  // Robust column resolution: fall back to the real columns whenever the
  // block's xKey/series do not match them exactly (LLM may guess names).
  const xKey = block.xKey && cols.includes(block.xKey) ? block.xKey : cols[0];
  const validSeries = (block.series ?? []).filter((s) => cols.includes(s.dataKey));
  const fallbackSeries = cols.filter((c) => c !== xKey).slice(0, 3).map((c) => ({ dataKey: c, label: c }));
  const series = validSeries.length ? validSeries : fallbackSeries;
  const data = res.rows.map((row) => {
    const obj: Record<string, unknown> = {};
    cols.forEach((c, i) => (obj[c] = row[i]));
    return obj;
  });

  const renderChart = () => {
    // Many categories -> rotate the x labels and reserve bottom space so they
    // don't overlap the chart or each other.
    const many = data.length > 8;
    const margin = { top: 10, right: 20, left: 0, bottom: many ? 30 : 5 };
    const xTickProps = {
      tick: { fontSize: 10 },
      tickLine: false,
      axisLine: false,
      ...(many ? { angle: -45, textAnchor: "end" as const, height: 70, interval: 0 } : {}),
    };

    if (block.chartType === "line") {
      return (
        <LineChart data={data} margin={margin}>
          <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
          <XAxis dataKey={xKey} {...xTickProps} />
          <YAxis tick={{ fontSize: 10 }} tickLine={false} axisLine={false} />
          <Tooltip content={<ChartTooltip />} />
          <Legend wrapperStyle={{ fontSize: 11 }} />
          {series.map((s, i) => (
            <Line key={s.dataKey} type="monotone" dataKey={s.dataKey} name={s.label || s.dataKey} stroke={chartColors[i % chartColors.length]} strokeWidth={2} dot={false} />
          ))}
        </LineChart>
      );
    }
    if (block.chartType === "scatter") {
      const yKey = series[0]?.dataKey || cols[1];
      return (
        <ScatterChart margin={margin}>
          <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
          <XAxis dataKey={xKey} name={xKey} {...xTickProps} />
          <YAxis dataKey={yKey} name={yKey} tick={{ fontSize: 10 }} tickLine={false} axisLine={false} />
          <Tooltip content={<ChartTooltip />} cursor={{ strokeDasharray: "3 3" }} />
          <Scatter data={data} fill="#6366f1" />
        </ScatterChart>
      );
    }
    // bar
    return (
      <BarChart data={data} margin={margin}>
        <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
        <XAxis dataKey={xKey} {...xTickProps} interval={0} />
        <YAxis tick={{ fontSize: 10 }} tickLine={false} axisLine={false} />
        <Tooltip content={<ChartTooltip />} cursor={{ fill: "hsl(var(--muted))" }} />
        <Legend wrapperStyle={{ fontSize: 11 }} />
        {series.map((s, i) => (
          <Bar key={s.dataKey} dataKey={s.dataKey} name={s.label || s.dataKey} fill={chartColors[i % chartColors.length]} radius={[3, 3, 0, 0]} />
        ))}
      </BarChart>
    );
  };

  return (
    <div className="w-full rounded-lg border bg-card p-3">
      {block.title && <p className="mb-2 text-xs font-medium text-muted-foreground">{block.title}</p>}
      <div dir="ltr" className="h-52 w-full">
        <ResponsiveContainer width="100%" height="100%">
          {renderChart()}
        </ResponsiveContainer>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Histogram
// ---------------------------------------------------------------------------
function HistogramBlockView({ block, results }: { block: HistogramBlock; results: Record<string, SqlResult> }) {
  const res = results[block.resultId] ?? null;
  const data = useMemo(() => {
    if (!res) return [];
    const idx = res.columns.indexOf(block.dataKey);
    if (idx < 0) return [];
    const values = res.rows.map((r) => Number(r[idx])).filter((v) => !isNaN(v));
    const bins = block.bins && block.bins > 0 ? block.bins : 10;
    if (!values.length) return [];
    const min = Math.min(...values);
    const max = Math.max(...values);
    const width = (max - min) / bins || 1;
    const counts = Array(bins).fill(0);
    values.forEach((v) => {
      let b = Math.floor((v - min) / width);
      if (b >= bins) b = bins - 1;
      if (b < 0) b = 0;
      counts[b]++;
    });
    return counts.map((c, i) => ({
      name: `${(min + i * width).toFixed(2)}–${(min + (i + 1) * width).toFixed(2)}`,
      count: c,
    }));
  }, [res, block]);
  return (
    <div className="rounded-lg border bg-card p-3">
      {block.title && <p className="mb-2 text-xs font-medium text-muted-foreground">{block.title}</p>}
      {data.length ? (
        <div className="h-44">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data} margin={{ top: 10, right: 20, left: 0, bottom: data.length > 8 ? 30 : 5 }}>
              <XAxis
                dataKey="name"
                tick={{ fontSize: 9 }}
                tickLine={false}
                axisLine={false}
                interval={0}
                {...(data.length > 8 ? { angle: -45, textAnchor: "end", height: 70 } : {})}
              />
              <YAxis tick={{ fontSize: 10 }} tickLine={false} axisLine={false} />
              <Tooltip content={<ChartTooltip />} cursor={{ fill: "hsl(var(--muted))" }} />
              <Bar dataKey="count" fill="#0d9488" radius={[2, 2, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <p className="text-xs text-muted-foreground">داده‌ای برای هیستوگرام موجود نیست.</p>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Table
// ---------------------------------------------------------------------------
function TableBlockView({ block, results }: { block: TableBlock; results: Record<string, SqlResult> }) {
  const table = resolveTable(block, results);
  if (!table || !table.columns.length) {
    return <p className="text-xs text-muted-foreground">داده‌ای برای جدول موجود نیست.</p>;
  }
  const maxRows = table.rows.slice(0, 50);
  return (
    <div className="overflow-hidden rounded-lg border bg-card">
      {table.title && <div className="px-3 py-1.5 text-xs font-medium text-muted-foreground">{table.title}</div>}
      <div className="max-h-64 overflow-auto">
        <table className="w-full text-right text-xs">
          <thead className="sticky top-0 bg-muted/80">
            <tr>
              {table.columns.map((c) => (
                <th key={c} className="whitespace-nowrap px-2.5 py-1.5 font-semibold text-muted-foreground">{c}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {maxRows.map((row, i) => (
              <tr key={i} className="border-t">
                {row.map((cell, j) => (
                  <td key={j} className="whitespace-nowrap px-2.5 py-1.5 tabular-nums">{cell == null ? "—" : String(cell)}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {table.rows.length > maxRows.length && (
        <div className="border-t px-2.5 py-1 text-[11px] text-muted-foreground">
          نمایش {formatNumber(maxRows.length)} از {formatNumber(table.rows.length)} ردیف
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Recommendation
// ---------------------------------------------------------------------------
function RecommendationBlockView({ block }: { block: RecommendationBlock }) {
  return (
    <div className="rounded-lg border bg-primary/5 p-3">
      {block.title && <p className="text-xs font-semibold text-primary">{block.title}</p>}
      <p className="mt-1 text-sm text-foreground">{block.text}</p>
      {block.reason && <p className="mt-1 text-xs text-muted-foreground">{block.reason}</p>}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Cards
// ---------------------------------------------------------------------------
function CustomerCardView({ block, results }: { block: CustomerCardBlock; results: Record<string, SqlResult> }) {
  const res = block.resultId ? results[block.resultId] : undefined;
  const row = res?.rows?.[0];
  const cols = res?.columns ?? [];
  const get = (k: string): string | undefined => {
    const idx = cols.indexOf(k);
    return idx >= 0 && row ? String(row[idx]) : undefined;
  };
  return (
    <Card className="w-full">
      <CardHeader className="pb-2 pt-3">
        <CardTitle className="text-sm">{get("Customer_ID") ?? block.customerId}</CardTitle>
      </CardHeader>
      <CardContent className="grid grid-cols-2 gap-x-3 gap-y-1 p-3 pt-0 text-xs">
        {cols.filter((c) => c !== "Customer_ID").slice(0, 6).map((c) => (
          <div key={c} className="flex min-w-0 justify-between gap-2">
            <span className="truncate text-muted-foreground">{c}</span>
            <span className="shrink-0 tabular-nums">{String(get(c) ?? "—")}</span>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

function ProductCardView({ block, results }: { block: ProductCardBlock; results: Record<string, SqlResult> }) {
  const res = block.resultId ? results[block.resultId] : undefined;
  const row = res?.rows?.[0];
  const cols = res?.columns ?? [];
  const get = (k: string): string | undefined => {
    const idx = cols.indexOf(k);
    return idx >= 0 && row ? String(row[idx]) : undefined;
  };
  return (
    <Card className="w-full">
      <CardHeader className="pb-2 pt-3">
        <CardTitle className="text-sm">{get("Product_ID") ?? block.productId}</CardTitle>
      </CardHeader>
      <CardContent className="grid grid-cols-2 gap-x-3 gap-y-1 p-3 pt-0 text-xs">
        {cols.filter((c) => c !== "Product_ID").slice(0, 6).map((c) => (
          <div key={c} className="flex min-w-0 justify-between gap-2">
            <span className="truncate text-muted-foreground">{c}</span>
            <span className="shrink-0 tabular-nums">{String(get(c) ?? "—")}</span>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

function OrderCardView({ block, results }: { block: OrderCardBlock; results: Record<string, SqlResult> }) {
  const res = block.resultId ? results[block.resultId] : undefined;
  const rows = res?.rows ?? [];
  const cols = res?.columns ?? [];
  const orderId = block.orderId;
  // Group rows by order id to render one order with its lines.
  return (
    <Card className="w-full">
      <CardHeader className="pb-2 pt-3">
        <CardTitle className="text-sm">سفارش {orderId}</CardTitle>
      </CardHeader>
      <CardContent className="p-3 pt-0">
        <div className="mb-2 text-xs text-muted-foreground">اقلام ({formatNumber(rows.length)})</div>
        <div className="overflow-x-auto">
          <table className="w-full text-right text-xs">
            <thead>
              <tr className="border-b text-muted-foreground">
                {cols.map((c) => (
                  <th key={c} className="px-2 py-1 font-medium">{c}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.slice(0, 20).map((row, i) => (
                <tr key={i} className="border-b">
                  {row.map((cell, j) => (
                    <td key={j} className="px-2 py-1 tabular-nums">{cell == null ? "—" : String(cell)}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// BlockRenderer
// ---------------------------------------------------------------------------
export function BlockRenderer({
  block,
  results,
}: {
  block: Block;
  results: Record<string, SqlResult>;
}) {
  switch (block.type) {
    case "markdown":
      return <MarkdownBlock content={block.content} />;
    case "metric":
      return <MetricBlockView block={block} results={results} />;
    case "chart":
      return <ChartBlockView block={block} results={results} />;
    case "histogram":
      return <HistogramBlockView block={block} results={results} />;
    case "table":
      return <TableBlockView block={block} results={results} />;
    case "recommendation":
      return <RecommendationBlockView block={block} />;
    case "customer_card":
      return <CustomerCardView block={block} results={results} />;
    case "product_card":
      return <ProductCardView block={block} results={results} />;
    case "order_card":
      return <OrderCardView block={block} results={results} />;
    default:
      return null;
  }
}
