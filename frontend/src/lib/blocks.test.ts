import { describe, it, expect } from "vitest";
import {
  validateBlocks,
  resolveResult,
  resolveMetricValue,
  resolveTable,
  type SqlResult,
} from "./blocks";

const results: Record<string, SqlResult> = {
  r1: { resultId: "r1", columns: ["month", "sales"], rows: [["m1", 10], ["m2", 20]], n_rows: 2 },
};

describe("validateBlocks", () => {
  it("markdown-only response", () => {
    const blocks = validateBlocks([{ type: "markdown", content: "## hello" }]);
    expect(blocks.map((b) => b.type)).toEqual(["markdown"]);
  });

  it("markdown -> metric", () => {
    const blocks = validateBlocks([
      { type: "markdown", content: "a" },
      { type: "metric", label: "X" },
    ]);
    expect(blocks.map((b) => b.type)).toEqual(["markdown", "metric"]);
  });

  it("markdown -> chart -> markdown preserves order", () => {
    const blocks = validateBlocks([
      { type: "markdown", content: "a" },
      { type: "chart", resultId: "r1", chartType: "line", xKey: "month", series: [{ dataKey: "sales" }] },
      { type: "markdown", content: "b" },
    ]);
    expect(blocks.map((b) => b.type)).toEqual(["markdown", "chart", "markdown"]);
  });

  it("markdown -> metric -> chart -> recommendation", () => {
    const blocks = validateBlocks([
      { type: "markdown", content: "m" },
      { type: "metric", label: "L" },
      { type: "chart", resultId: "r1", chartType: "bar" },
      { type: "recommendation", text: "do it" },
    ]);
    expect(blocks.map((b) => b.type)).toEqual(["markdown", "metric", "chart", "recommendation"]);
  });

  it("arbitrary ordering is preserved", () => {
    const blocks = validateBlocks([
      { type: "customer_card", customerId: "C1" },
      { type: "markdown", content: "x" },
      { type: "order_card", orderId: "T1" },
      { type: "product_card", productId: "P1" },
      { type: "markdown", content: "y" },
    ]);
    expect(blocks.map((b) => b.type)).toEqual([
      "customer_card", "markdown", "order_card", "product_card", "markdown",
    ]);
  });

  it("drops unknown and malformed blocks without crashing", () => {
    const blocks = validateBlocks([
      { type: "nonsense" },
      { type: "chart" }, // missing resultId -> invalid
      "string",
      null,
      { type: "markdown", content: "ok" },
    ]);
    expect(blocks.map((b) => b.type)).toEqual(["markdown"]);
  });

  it("assigns a default id when missing", () => {
    const [b] = validateBlocks([{ type: "markdown", content: "hi" }]);
    expect(b.id).toBe("b0");
  });

  it("non-array input returns []", () => {
    expect(validateBlocks({ type: "markdown" })).toEqual([]);
    expect(validateBlocks(undefined)).toEqual([]);
  });
});

describe("result resolution", () => {
  it("chart references exact MCP result by resultId", () => {
    const res = resolveResult(results, "r1");
    expect(res).not.toBeNull();
    expect(res!.rows).toEqual([["m1", 10], ["m2", 20]]);
  });

  it("metric resolves value by valueKey", () => {
    const v = resolveMetricValue({ id: "b", type: "metric", resultId: "r1", label: "L", valueKey: "sales" }, results);
    expect(v).toBe("10");
  });

  it("metric falls back to first non-null cell", () => {
    const v = resolveMetricValue({ id: "b", type: "metric", resultId: "r1", label: "L" }, results);
    expect(v).toBe("m1");
  });

  it("table resolves from result", () => {
    const t = resolveTable({ id: "b", type: "table", resultId: "r1" }, results);
    expect(t!.columns).toEqual(["month", "sales"]);
    expect(t!.rows).toHaveLength(2);
  });

  it("table uses inline data when no result", () => {
    const t = resolveTable({ id: "b", type: "table", columns: ["a"], rows: [[1]] }, results);
    expect(t!.rows).toEqual([[1]]);
  });

  it("missing resultId resolves to null", () => {
    expect(resolveResult(results, "missing")).toBeNull();
  });
});
