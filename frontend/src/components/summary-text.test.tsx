import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { SummaryText } from "./summary-text";

describe("SummaryText", () => {
  it("renders ### markdown headings as clean section headers (no '###', no dot)", () => {
    const { container } = render(
      <SummaryText text={"### وضعیت کلی\n\nتعداد مشتریان ۶۴۴ است."} />
    );
    const header = container.querySelector("p.font-semibold");
    expect(header?.textContent).toBe("وضعیت کلی");
    expect(screen.queryByText(/###/)).toBeNull();
    // The heading must NOT get a forced dot.
    expect(screen.queryByText("وضعیت کلی.")).toBeNull();
    expect(screen.getByText("تعداد مشتریان ۶۴۴ است.")).toBeTruthy();
  });

  it("renders **bold** headings and plain label: lines as headers", () => {
    const { container } = render(
      <SummaryText text={"**نکات مهم**\n\nپیشنهاد اقدام:\nپیگیری مطالبات."} />
    );
    const headers = Array.from(container.querySelectorAll("p.font-semibold")).map(
      (p) => p.textContent
    );
    expect(headers).toEqual(["نکات مهم", "پیشنهاد اقدام:"]);
  });

  it("renders '- ' bullets as bulleted rows without markdown markers", () => {
    const { container } = render(
      <SummaryText text={"نکات:\n - فیلامنت و پرز با ۴۵ مورد\n - شید رنگ با ۳۶ مورد"} />
    );
    expect(screen.getByText("فیلامنت و پرز با ۴۵ مورد")).toBeTruthy();
    expect(screen.getByText("شید رنگ با ۳۶ مورد")).toBeTruthy();
    expect(container.querySelector("span.h-1.w-1")).toBeTruthy();
    expect(screen.queryByText(/^\s*-/)).toBeNull();
  });

  it("does not force a period onto lines that already lack one", () => {
    render(<SummaryText text={"بدون نقطه پایانی"} />);
    expect(screen.getByText("بدون نقطه پایانی")).toBeTruthy();
    expect(screen.queryByText("بدون نقطه پایانی.")).toBeNull();
  });

  it("keeps the exact sentence as written (no aggressive dots)", () => {
    render(<SummaryText text={"تعداد سفارش‌ها ۱۴٬۴۲۳ و شکایات ۵۲۰ مورد ثبت شده."} />);
    expect(
      screen.getByText("تعداد سفارش‌ها ۱۴٬۴۲۳ و شکایات ۵۲۰ مورد ثبت شده.")
    ).toBeTruthy();
  });

  it("renders the full dashboard-style summary end to end", () => {
    const summary = [
      "### وضعیت کلی",
      "تعداد مشتریان ۶۴۴ و درآمد کل ۴٬۴۲۲٬۶۸۴٬۳۸۳ تومان است.",
      "### نکات مهم",
      " - فیلامنت و پرز با ۴۵ مورد",
      "### پیشنهاد اقدام",
      "پیگیری جدی مطالبات و چک‌های برگشتی.",
    ].join("\n\n");
    const { container } = render(<SummaryText text={summary} />);
    expect(container.querySelectorAll("p.font-semibold")).toHaveLength(3);
    expect(container.textContent).toContain("۴٬۴۲۲٬۶۸۴٬۳۸۳");
    expect(container.textContent).not.toContain("###");
  });
});
