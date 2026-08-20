// Shared Block schema (mirrors backend/schemas/blocks.py).
// An assistant response is an ordered array of Blocks plus a results map keyed
// by resultId. The frontend renders blocks in order and resolves resultId -> data.

export const BLOCK_TYPES = [
  "markdown",
  "metric",
  "chart",
  "histogram",
  "table",
  "recommendation",
  "customer_card",
  "product_card",
  "order_card",
] as const;

export type BlockType = (typeof BLOCK_TYPES)[number];

export type ChartType = "line" | "bar" | "scatter";

export interface SqlResult {
  resultId: string;
  columns: string[];
  rows: unknown[][];
  n_rows: number;
}

// ---- blocks ----
export interface MarkdownBlock {
  id: string;
  type: "markdown";
  content: string;
}

export interface MetricBlock {
  id: string;
  type: "metric";
  resultId?: string;
  label: string;
  valueKey?: string;
  rowIndex?: number;
  change?: string;
  trend?: "up" | "down" | "neutral";
}

export interface ChartBlock {
  id: string;
  type: "chart";
  resultId: string;
  chartType: ChartType;
  xKey?: string;
  series?: { dataKey: string; label?: string }[];
  title?: string;
}

export interface HistogramBlock {
  id: string;
  type: "histogram";
  resultId: string;
  dataKey: string;
  bins?: number;
  title?: string;
}

export interface TableBlock {
  id: string;
  type: "table";
  resultId?: string;
  columns?: string[];
  rows?: unknown[][];
  title?: string;
}

export interface RecommendationBlock {
  id: string;
  type: "recommendation";
  resultId?: string;
  title?: string;
  text: string;
  reason?: string;
}

export interface CustomerCardBlock {
  id: string;
  type: "customer_card";
  resultId?: string;
  customerId: string;
}

export interface ProductCardBlock {
  id: string;
  type: "product_card";
  resultId?: string;
  productId: string;
}

export interface OrderCardBlock {
  id: string;
  type: "order_card";
  resultId?: string;
  orderId: string;
}

export type Block =
  | MarkdownBlock
  | MetricBlock
  | ChartBlock
  | HistogramBlock
  | TableBlock
  | RecommendationBlock
  | CustomerCardBlock
  | ProductCardBlock
  | OrderCardBlock;

export interface AssistantResponse {
  blocks: Block[];
  results: Record<string, SqlResult>;
}

// ---------------------------------------------------------------------------
// Validation (never throws; malformed blocks are dropped)
// ---------------------------------------------------------------------------
function isObj(v: unknown): v is Record<string, unknown> {
  return typeof v === "object" && v !== null && !Array.isArray(v);
}

export function validateBlocks(raw: unknown): Block[] {
  if (!Array.isArray(raw)) return [];
  const out: Block[] = [];
  let i = 0;
  for (const item of raw) {
    if (!isObj(item)) continue;
    const type = item["type"];
    if (typeof type !== "string" || !(BLOCK_TYPES as readonly string[]).includes(type)) continue;
    const id = typeof item["id"] === "string" ? item["id"] : `b${i}`;
    const block = { ...item, id } as Block;
    if (!isValidBlock(block)) continue;
    out.push(block);
    i++;
  }
  return out;
}

function isValidBlock(b: Block): boolean {
  switch (b.type) {
    case "markdown":
      return typeof b.content === "string";
    case "metric":
      return typeof b.label === "string";
    case "chart":
      return (
        typeof b.resultId === "string" &&
        (b.chartType === "line" || b.chartType === "bar" || b.chartType === "scatter")
      );
    case "histogram":
      return typeof b.resultId === "string" && typeof b.dataKey === "string";
    case "table":
      return true; // table can resolve from resultId OR inline columns/rows
    case "recommendation":
      return typeof b.text === "string";
    case "customer_card":
    case "product_card":
    case "order_card":
      return typeof (b as { customerId?: string; productId?: string; orderId?: string }).customerId === "string" ||
             typeof (b as { customerId?: string; productId?: string; orderId?: string }).productId === "string" ||
             typeof (b as { customerId?: string; productId?: string; orderId?: string }).orderId === "string";
    default:
      return false;
  }
}

// ---------------------------------------------------------------------------
// Result resolution
// ---------------------------------------------------------------------------
export function resolveResult(
  results: Record<string, SqlResult>,
  resultId?: string
): SqlResult | null {
  if (!resultId) return null;
  return results[resultId] ?? null;
}

/** Resolve a metric's single value from its result. */
export function resolveMetricValue(block: MetricBlock, results: Record<string, SqlResult>): string | null {
  const res = resolveResult(results, block.resultId);
  if (!res || !res.rows.length) return null;
  const row = res.rows[block.rowIndex ?? 0];
  if (block.valueKey) {
    const idx = res.columns.indexOf(block.valueKey);
    if (idx >= 0 && row[idx] != null) return String(row[idx]);
  }
  // fallback: first non-null cell in the first row
  const first = row.find((v) => v != null);
  return first != null ? String(first) : null;
}

/** Resolve a table block's columns/rows (result first, then inline). */
export function resolveTable(
  block: TableBlock,
  results: Record<string, SqlResult>
): { columns: string[]; rows: unknown[][]; title?: string } | null {
  if (block.resultId) {
    const res = resolveResult(results, block.resultId);
    if (res) return { columns: res.columns, rows: res.rows, title: block.title };
  }
  if (block.columns && block.rows) {
    return { columns: block.columns, rows: block.rows, title: block.title };
  }
  return null;
}

/** Resolve chart data rows from a result. */
export function resolveChartData(
  block: ChartBlock,
  results: Record<string, SqlResult>
): SqlResult | null {
  return resolveResult(results, block.resultId);
}
