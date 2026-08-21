import { describe, it, expect } from "vitest";
import { formatDate, formatNumber, formatCurrency } from "./utils";

describe("formatDate", () => {
  it("renders a Jalali date with Persian digits and NO thousands separator", () => {
    // 2019-12-30 -> ۱۳۹۸/۱۰/۹. The 4-digit Jalali year must not get a comma.
    const out = formatDate("2019-12-30");
    expect(out).toBe("۱۳۹۸/۱۰/۹");
    expect(out).not.toContain("٬");
    expect(out).not.toContain(",");
  });

  it("renders other dates without separators too", () => {
    expect(formatDate("2022-04-04")).toBe("۱۴۰۱/۱/۱۵");
    expect(formatDate("2022-04-04 10:30:00")).toBe("۱۴۰۱/۱/۱۵");
  });

  it("handles missing dates", () => {
    expect(formatDate(null)).toBe("—");
    expect(formatDate(undefined)).toBe("—");
    expect(formatDate("")).toBe("—");
  });
});

describe("numeric formatting", () => {
  it("keeps the thousands separator for amounts (that is expected)", () => {
    expect(formatNumber(1570)).toBe("۱٬۵۷۰");
    // fa-IR compact uses a non-breaking space between number and unit.
    expect(formatCurrency(166798730)).toBe("۱۶۶٫۸\u00A0میلیون");
  });
});
