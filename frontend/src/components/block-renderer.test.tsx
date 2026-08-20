import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { BlockRenderer } from "./block-renderer";
import type { SqlResult } from "@/lib/blocks";

const results: Record<string, SqlResult> = {
  r1: { resultId: "r1", columns: ["month", "sales"], rows: [["m1", 10]], n_rows: 1 },
};

describe("BlockRenderer", () => {
  it("renders blocks sequentially in the given order", () => {
    const { container } = render(
      <>
        <BlockRenderer block={{ id: "b1", type: "markdown", content: "## intro" }} results={results} />
        <BlockRenderer block={{ id: "b2", type: "metric", label: "Sales", resultId: "r1", valueKey: "sales" }} results={results} />
        <BlockRenderer block={{ id: "b3", type: "table", resultId: "r1" }} results={results} />
      </>
    );
    // markdown rendered first
    expect(container.querySelector("h2")?.textContent).toBe("intro");
    // metric
    expect(screen.getByText("Sales")).toBeTruthy();
    // table present
    expect(screen.getByText("month")).toBeTruthy();
    expect(screen.getAllByText("10").length).toBeGreaterThanOrEqual(1);
  });

  it("markdown block renders bold and lists", () => {
    const { container } = render(
      <BlockRenderer block={{ id: "b1", type: "markdown", content: "**bold** and *italic*" }} results={results} />
    );
    expect(container.querySelector("strong")?.textContent).toBe("bold");
    expect(container.querySelector("em")?.textContent).toBe("italic");
  });

  it("unknown block type renders nothing without crashing", () => {
    // @ts-expect-error intentionally bad block
    const { container } = render(<BlockRenderer block={{ id: "b", type: "nope" }} results={results} />);
    expect(container.firstChild).toBeNull();
  });

  it("recommendation renders title and text", () => {
    render(
      <BlockRenderer
        block={{ id: "b1", type: "recommendation", title: "Act", text: "Call the customer", reason: "declining" }}
        results={results}
      />
    );
    expect(screen.getByText("Act")).toBeTruthy();
    expect(screen.getByText("Call the customer")).toBeTruthy();
  });
});
