import { describe, expect, it } from "vitest";

import { fixPersianZwnj } from "./persian";

describe("fixPersianZwnj", () => {
  it("fixes the user-reported stuck words", () => {
    const cases: Array<[string, string]> = [
      ["حلنشده", "حل\u200cنشده"],
      ["جلسهی", "جلسه\u200cی"],
      ["یکییکی", "یکی\u200cیکی"],
      ["مشتریها", "مشتری\u200cها"],
      ["مشتریهایی", "مشتری\u200cهایی"],
      ["بهاحتمال", "به\u200cاحتمال"],
      ["پرارزش", "پر\u200cارزش"],
      ["میشود", "می\u200cشود"],
      ["گرفتهاند", "گرفته\u200cاند"],
      ["نقطهی", "نقطه\u200cی"],
    ];
    for (const [raw, expected] of cases) {
      expect(fixPersianZwnj(raw)).toBe(expected);
    }
  });

  it("never corrupts real single words", () => {
    const guards = ["میز", "میوه", "میدان", "ماهی", "رها", "بها", "شاه", "چاه", "سلام", "تهی"];
    for (const word of guards) {
      expect(fixPersianZwnj(word)).toBe(word);
    }
  });

  it("leaves non-Persian text untouched", () => {
    expect(fixPersianZwnj("C_117580")).toBe("C_117580");
    expect(fixPersianZwnj("hello world")).toBe("hello world");
    expect(fixPersianZwnj("")).toBe("");
  });

  it("is idempotent", () => {
    const raw = "مشتریها حلنشده جلسهی یکییکی";
    const once = fixPersianZwnj(raw);
    expect(fixPersianZwnj(once)).toBe(once);
  });
});
