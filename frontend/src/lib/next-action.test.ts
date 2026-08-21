import { describe, it, expect } from "vitest";
import { parseNextAction } from "./next-action";

describe("parseNextAction", () => {
  it("parses the canonical four-line format", () => {
    const text = [
      "اقدام اصلی: رسیدگی به شکایت‌ها",
      "چرا الان: پس از شکایت، خرید ۶۸٪ کاهش یافته و یک شکایت باز است",
      "گام بعدی: شکایت را حل کنید و رضایت مشتری را مطمئن شوید",
      "اولویت: بالا",
    ].join("\n");
    const p = parseNextAction(text);
    expect(p?.action).toBe("رسیدگی به شکایت‌ها");
    expect(p?.why).toContain("۶۸٪");
    expect(p?.nextStep).toContain("شکایت را حل کنید");
    expect(p?.priority).toBe("بالا");
  });

  it("handles extra blank lines and trimming", () => {
    const p = parseNextAction(
      "  \nاقدام اصلی:  بازبینی شرایط پرداخت \n\nچرا الان: ۱۳۱ از ۲۱۲ پرداخت با تأخیر بوده است\nگام بعدی: شرایط پرداخت را بازبینی کنید\nاولویت: متوسط\n"
    );
    expect(p?.action).toBe("بازبینی شرایط پرداخت");
    expect(p?.priority).toBe("متوسط");
  });

  it("maps unknown priority to نامشخص without failing", () => {
    const p = parseNextAction("اقدام اصلی: فقط پایش\nچرا الان: -\nگام بعدی: پایش کنید");
    expect(p?.priority).toBe("نامشخص");
    expect(p?.action).toBe("فقط پایش");
  });

  it("returns null for unparseable text", () => {
    expect(parseNextAction("چیزی نیست")).toBeNull();
    expect(parseNextAction("")).toBeNull();
  });
});
