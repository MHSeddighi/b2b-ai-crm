/**
 * pitch-data.ts — Presentation data adapter.
 *
 * EVERY number in this file is a literal taken from the real system outputs:
 *   - data/processed/customer_360.duckdb          (DuckDB tables, read-only)
 *   - data/cache/at_risk_engine/overview.json     (engine churn-risk ranking)
 *   - data/cache/analyses/overview.json           (analyses payload)
 *   - data/cache/customer360_data/C_*.json        (per-customer 360 payloads)
 *   - data/cache/customer360/C_*.json             (cached LLM summaries)
 *   - experiments/complaints_quality_purchase.ipynb  (precomputed EDA)
 *
 * Nothing is computed at presentation time and nothing is invented: the deck
 * is a storytelling layer over already-existing results. If a figure is not
 * here, it does not exist in our outputs and is therefore not shown.
 */
export interface PitchSignal {
  label: string;
  tone: "negative" | "neutral" | "positive";
  detail: string;
  reasons: string[];
}

export interface PitchAction {
  name: string;
  reason: string;
  nextStep: string;
}

export interface PitchCustomer {
  id: string;
  segment: string;
  status: string;
  revenue: number;
  orders: number;
  avgOrderValue: number;
  lastPurchase: string; // ISO
  daysSince: number;
  cycleDays: number;
  complaints: number;
  openComplaints: number;
  complaintImpactPct: number;
  latePaymentsText: string;
  overdue: number;
  bouncedChecks: number;
  walletSharePct: number;
  devOpen: number;
  offerNote: string;
  riskScore: number;
  riskLevel: string;
  story: string;
  state: { key: string; label: string; status: string }[];
  signals: PitchSignal[];
  actions: PitchAction[];
  summary: string;
}

export const PITCH = {
  productName: "بینش مشتری",
  productTag: "هوش مشتری · سیگنال · اقدام",

  /* ------------------------------------------------------------- the gap */
  gap: {
    opening:
      "شرکت‌ها داده مشتری کم ندارند؛ تواناییِ تبدیل داده‌های پراکنده به تصمیمِ به‌موقع را ندارند.",
    sources: [
      { title: "فروش و فاکتور", text: "۵۲٬۹۸۷ ردیف فروش و ۱۴٬۴۲۳ فاکتور در جدول‌های جدا", stat: "۵۲٬۹۸۷" },
      { title: "شکایات", text: "۵۲۰ شکایت ثبت‌شده، جدا از تاریخچه فروش", stat: "۵۲۰" },
      { title: "تعاملات و وصول", text: "۴٬۱۸۴ تعامل CRM و ۱۵٬۶۵۲ رویداد وصول", stat: "۴٬۱۸۴" },
      { title: "پیشنهاد و درخواست", text: "۲٬۵۰۰ پیشنهاد و ۸۰۰ درخواست توسعه محصول", stat: "۲٬۵۰۰" },
    ],
    sourcesNote: "داده‌ها در ۱۶ منبع جدا از هم زندگی می‌کنند.",
    pain: [
      {
        title: "فروش می‌گوید چه شد، نه چرا",
        text: "تاریخچه خرید بدون وضعیت رابطه، پرداخت و شکایت معنا ندارد.",
      },
      {
        title: "ریسک دیر دیده می‌شود",
        text: "توقف خرید و افزایش شکایت‌ها معمولاً وقتی دیده می‌شوند که خیلی دیر شده.",
      },
      {
        title: "تحلیل دستی ناممکن است",
        text: "هیچ تیم فروشی نمی‌تواند ۶۴۴ مشتری را رکورد به رکورد بررسی کند.",
      },
      {
        title: "تصمیم بدون تصویر کامل",
        text: "وقتی تصویر کامل می‌شود، فرصت از دست رفته است.",
      },
    ],
  },

  /* ----------------------------------------------------------- pipeline */
  pipeline: [
    { title: "داده پراکنده", text: "۱۶ منبع: فروش، شکایت، وصول، تعامل، پیشنهاد…" },
    { title: "سیگنال مشتری", text: "چرخه خرید، اثر شکایت، رفتار پرداخت، سهم از سبد…" },
    { title: "مشتری ۳۶۰", text: "یک نمای واحد و قابل‌توضیح از هر مشتری" },
    { title: "ریسک + فرصت", text: "چه چیزی در خطر است، چه چیزی رشد می‌کند" },
    { title: "اقدام بعدی", text: "به فروش بگوییم دقیقاً چه کار کند" },
  ],
  pipelineIdea:
    "ما داده را فقط خلاصه نمی‌کنیم؛ آن را به سیگنال‌های قابل اندازه‌گیری و تصمیم‌های قابل اقدام تبدیل می‌کنیم.",

  /* ------------------------------------------------------ portfolio KPIs */
  kpis: {
    customers: 644,
    revenue: 4422684383.11, // SUM("مبلغ کل") — sales
    salesRows: 52987,
    invoices: 14423,
    complaints: 520,
    openComplaints: 186,
    interactions: 4184,
    offers: 2500,
    offersAccepted: 651,
    devRequests: 800,
    sources: 16,
  },

  /* -------------------------------------------------------- real signals */
  segments: [
    { name: "A", value: 231 },
    { name: "B", value: 206 },
    { name: "C", value: 207 },
  ],
  statuses: [
    { name: "فعال", value: 273 },
    { name: "غیرفعال", value: 371 },
  ],
  complaintSeverity: [
    { name: "کم", value: 129 },
    { name: "متوسط", value: 226 },
    { name: "زیاد", value: 131 },
    { name: "بحرانی", value: 34 },
  ],
  complaintThemes: [
    { name: "فیلامنت و پرز", value: 45 },
    { name: "شید رنگ", value: 36 },
    { name: "بدپیچی / سفتی بسته", value: 28 },
    { name: "مینگل بیشتر از حد", value: 21 },
    { name: "استحکام پایین / پارگی", value: 18 },
    { name: "الصاق لیبل اشتباه", value: 18 },
  ],
  offerEffectiveness: [
    { type: "مدت‌دار", count: 918, rate: 0.28 },
    { type: "حجمی", count: 784, rate: 0.25 },
    { type: "قیمتی", count: 798, rate: 0.25 },
  ],
  revenueConcentration: [
    { name: "C", value: 1684532856, customers: 207 },
    { name: "A", value: 1612417112, customers: 231 },
    { name: "B", value: 1125734415, customers: 206 },
  ],
  churnFactors: {
    neverBought: 0,
    inactive180_365: 11,
    inactiveOver365: 627,
    inactiveWithComplaints: 163,
  },
  complaintImpact: {
    customers: 508, // complaint customers with a prior purchase (precomputed EDA)
    declinePct: 73.4, // share with lower order/revenue after the complaint
  },

  /* ----------------------------------------------------------- impact */
  impact: {
    customers: 644,
    revenue: 4422684383.11,
    atRiskCount: 50, // engine top-50 ranking (risk_score 68 — "متوسط")
    atRiskRevenue: 1295212739.19, // sum of revenue across the engine top-50
    atRiskTop12Revenue: 866711058.29, // dashboard "revenue at risk" figure
    winbackCount: 627,
    winbackRevenue: 4394065149.01,
    overdue: 3520407030.0,
    bouncedChecks: 82,
  },

  /* -------------------------------------------- top-K (engine outputs) */
  topRetain: [
    {
      id: "C_535756",
      revenue: 166798730.41,
      complaints: 4,
      openComplaints: 1,
      daysSince: 1570,
      reason: "پس از شکایت، خرید ۶۸٪ کاهش یافته · چرخه عادی خرید ۷ روز",
      action: "رسیدگی به شکایت‌ها",
    },
    {
      id: "C_051535",
      revenue: 118339269.43,
      complaints: 2,
      openComplaints: 1,
      daysSince: 1549,
      reason: "پس از شکایت، خرید ۱۰۰٪ متوقف شده · ۱ چک برگشتی",
      action: "رسیدگی به شکایت‌ها",
    },
    {
      id: "C_806376",
      revenue: 82480454.56,
      complaints: 17,
      openComplaints: 6,
      daysSince: 1724,
      reason: "پس از شکایت‌ها، خرید قطع شده · ۸ چک برگشتی · ۲۷ درخواست توسعه",
      action: "رسیدگی به شکایت‌ها + بازبینی پرداخت",
    },
  ],
  recommendations: [
    {
      tone: "negative",
      title: "حفظ مشتریان در معرض از دست رفتن",
      detail:
        "۱۲ مشتری با مجموع درآمد ۸۶۶٬۷۱۱٬۰۵۸ تومان در وضعیت نگران‌کننده‌اند؛ پیگیری تلفنی و رسیدگی به شکایت‌های باز، اولویت اول است.",
      impact: 866711058,
    },
    {
      tone: "positive",
      title: "بازگرداندن مشتریان قدیمی",
      detail:
        "۶۲۷ مشتری ارزشمند بیش از یک سال است خریدی نداشته‌اند (مجموع درآمد سابق ۴٬۳۹۴٬۰۶۵٬۱۴۹ تومان)؛ یک پیشنهاد ویژه می‌تواند آن‌ها را برگرداند.",
      impact: 4394065149,
    },
    {
      tone: "warning",
      title: "رسیدگی به «فیلامنت و پرز»",
      detail:
        "این موضوع با ۴۵ شکایت پرتکرارترین مشکل است؛ رفع ریشه‌ای آن جلوی از دست رفتن فروش را می‌گیرد.",
      impact: 0,
    },
    {
      tone: "positive",
      title: "تمرکز پیشنهادها روی نوع مؤثر",
      detail:
        "پیشنهادهای «مدت‌دار» بالاترین پذیرش را دارند (۲۸٪ از ۹۱۸ پیشنهاد)؛ تخصیص تخفیف به همین نوع بازدهی بیشتری دارد.",
      impact: 0,
    },
    {
      tone: "warning",
      title: "وصول مطالبات عقب‌افتاده",
      detail:
        "۳٬۵۲۰٬۴۰۷٬۰۳۰ تومان مطالبات با تأخیر و ۸۲ چک برگشتی ثبت شده؛ پیگیری وصول نقدینگی را افزایش می‌دهد.",
      impact: 3520407030,
    },
  ],

  /* ------------------------------------------------------------ charts */
  purchaseTrend: [
    { month: "بهمن 99", value: 128157844 },
    { month: "اسفند 99", value: 87275546 },
    { month: "فروردین 00", value: 55698253 },
    { month: "اردیبهشت 00", value: 92613333 },
    { month: "خرداد 00", value: 129931343 },
    { month: "تیر 00", value: 82204255 },
    { month: "مرداد 00", value: 125295584 },
    { month: "شهریور 00", value: 116811033 },
    { month: "مهر 00", value: 129566168 },
    { month: "آبان 00", value: 228753898 },
    { month: "آذر 00", value: 175315711 },
    { month: "دی 00", value: 248560223 },
    { month: "بهمن 00", value: 346912684 },
    { month: "اسفند 00", value: 123816582 },
    { month: "فروردین 01", value: 165289123 },
    { month: "اردیبهشت 01", value: 292102055 },
    { month: "خرداد 01", value: 316855413 },
    { month: "تیر 01", value: 468776170 },
    { month: "مرداد 01", value: 297326110 },
    { month: "شهریور 01", value: 6500610 },
  ],
  complaintTrend: [
    { month: "دی 00", value: 21 },
    { month: "بهمن 00", value: 22 },
    { month: "اسفند 00", value: 13 },
    { month: "فروردین 01", value: 11 },
    { month: "اردیبهشت 01", value: 10 },
    { month: "خرداد 01", value: 6 },
    { month: "تیر 01", value: 8 },
    { month: "مرداد 01", value: 9 },
    { month: "شهریور 01", value: 6 },
    { month: "مهر 01", value: 11 },
    { month: "آبان 01", value: 2 },
    { month: "آذر 01", value: 1 },
    { month: "تیر 03", value: 2 },
    { month: "مرداد 03", value: 4 },
    { month: "شهریور 03", value: 2 },
    { month: "مهر 03", value: 4 },
    { month: "آبان 03", value: 4 },
    { month: "آذر 03", value: 7 },
    { month: "دی 03", value: 7 },
    { month: "بهمن 03", value: 2 },
    { month: "اردیبهشت 04", value: 3 },
    { month: "مرداد 04", value: 1 },
    { month: "مهر 04", value: 3 },
    { month: "آبان 04", value: 1 },
  ],

  /* ------------------------------------------------ featured customer */
  featured: {
    id: "C_535756",
    segment: "C",
    status: "فعال",
    revenue: 166798730.41,
    orders: 197,
    avgOrderValue: 846694,
    lastPurchase: "2022-04-04",
    daysSince: 1570,
    cycleDays: 7,
    complaints: 4,
    openComplaints: 1,
    complaintImpactPct: 68,
    latePaymentsText: "۱۳۱ از ۲۱۲ پرداخت با تأخیر",
    overdue: 134881535.08,
    bouncedChecks: 0,
    walletSharePct: 13,
    devOpen: 8,
    offerNote: "به پیشنهادهای «تخفیفی» پاسخ مثبت می‌دهد (۴ قبول / ۳ رد)",
    riskScore: 68,
    riskLevel: "متوسط",
    summary: `مشتری از سال ۱۳۹۸ با ما همکاری داشته و مجموع درآمد او ۱۶۶٬۷۹۸٬۷۳۰ تومان از ۱۹۷ سفارش است؛ اما نزدیک به چهار سال و نیم از آخرین خریدش می‌گذرد، در حالی که چرخه عادی خرید او ۷ روز بوده. پس از شکایت، خرید ۶۸٪ کاهش یافته و هنوز یک شکایت باز است؛ پرداخت‌های عقب‌افتاده زیاد است. با این حال ۸ درخواست توسعه باز دارد و به پیشنهادهای تخفیفی پاسخ خوبی می‌دهد.`,
    story:
      "در نگاه اول این مشتری ارزشمند است: درآمد بالا و ۱۹۷ سفارش. اما وقتی سیگنال‌ها را کنار هم می‌گذاریم، داستان فرق می‌کند.",
    actions: [
      {
        name: "رسیدگی به شکایت‌ها",
        reason: "پس از شکایت، خرید ۶۸٪ کاهش یافته",
        nextStep: "شکایت را حل کنید و پیش از هر فروش جدید، رضایت مشتری را مطمئن شوید.",
      },
      {
        name: "بازبینی شرایط پرداخت",
        reason: "۱۳۱ از ۲۱۲ پرداخت با تأخیر بوده است",
        nextStep: "شرایط پرداخت را با مشتری‌ای که پرداختش به تأخیر افتاده بازبینی کنید.",
      },
      {
        name: "پیگیری درخواست توسعه محصول",
        reason: "۸ درخواست توسعه باز",
        nextStep: "درخواست توسعه باز مشتری را پیگیری کنید.",
      },
    ],
    state: [
      { key: "value", label: "ارزش", status: "بالا" },
      { key: "churn_risk", label: "ریسک ریزش", status: "هشدار" },
      { key: "relationship_health", label: "رابطه", status: "ضعیف" },
      { key: "payment_risk", label: "پرداخت", status: "هشدار" },
      { key: "profitability", label: "سودآوری", status: "نامشخص" },
    ],
    signals: [
      {
        label: "چرخه خرید",
        tone: "negative",
        detail: "بحرانی",
        reasons: ["۱٬۵۷۰ روز از آخرین خرید گذشته، در حالی که چرخه عادی خرید ۷ روز است"],
      },
      {
        label: "اثر شکایات",
        tone: "negative",
        detail: "بحرانی",
        reasons: ["پس از شکایت، خرید ۶۸٪ کاهش یافته", "۱ شکایت باز مانده است"],
      },
      {
        label: "رفتار پرداخت",
        tone: "neutral",
        detail: "هشدار",
        reasons: ["۱۳۱ از ۲۱۲ پرداخت با تأخیر بوده است"],
      },
      {
        label: "سهم از خرید مشتری",
        tone: "neutral",
        detail: "خنثی",
        reasons: ["سهم از خرید مشتری ۱۳٪ است"],
      },
      {
        label: "پاسخ به پیشنهادها",
        tone: "positive",
        detail: "مثبت",
        reasons: ["مشتری بیشتر به پیشنهادهای «تخفیفی» پاسخ می‌دهد (۴ قبول / ۳ رد)"],
      },
      {
        label: "درخواست‌های توسعه",
        tone: "positive",
        detail: "مثبت",
        reasons: ["۸ درخواست توسعه باز"],
      },
      {
        label: "ریسک از دست دادن مشتری",
        tone: "neutral",
        detail: "هشدار",
        reasons: ["مشتری خیلی فراتر از چرخه عادی خرید است", "پس از شکایت، خرید کاهش یافته"],
      },
    ],
  } satisfies PitchCustomer,

  /* ------------------------------------------------- copilot scenario */
  copilot: {
    intro: "دستیار هوشمند از نتایج از پیش‌محاسبه‌شده پاسخ می‌دهد — بدون انتظار برای محاسبات سنگین.",
    q1: "کدام مشتری‌ها را امروز برای افزایش درآمد تماس بگیریم؟",
    a1Title: "۳ مشتری که همین امروز باید پیگیری شوند",
    a1Rows: [
      { id: "C_535756", revenue: "۱۶۶٫۸ میلیون", signal: "خرید ۶۸٪ کاهش یافته", action: "رسیدگی به شکایت‌ها" },
      { id: "C_051535", revenue: "۱۱۸٫۳ میلیون", signal: "خرید متوقف شده · چک برگشتی", action: "رسیدگی به شکایت‌ها" },
      { id: "C_806376", revenue: "۸۲٫۵ میلیون", signal: "۱۷ شکایت · ۸ چک برگشتی", action: "شکایت‌ها + بازبینی پرداخت" },
    ],
    q2: "چرا C_535756 را همین امروز پیگیری کنیم؟",
    a2: [
      "چرخه عادی خرید این مشتری ۷ روز است؛ آخرین خرید ۱٬۵۷۰ روز پیش بوده است.",
      "پس از شکایت، خرید ۶۸٪ کاهش یافته و یک شکایت هنوز باز است.",
      "درآمد کل ۱۶۶٫۸ میلیون تومان — ارزش پیگیری بالاست.",
    ],
    q3: "چه کاری انجام دهیم؟",
    a3: [
      { name: "رسیدگی به شکایت‌ها", next: "شکایت را حل کنید و پیش از فروش جدید، رضایت مشتری را مطمئن شوید." },
      { name: "بازبینی شرایط پرداخت", next: "شرایط پرداخت را با مشتری‌ای که پرداختش به تأخیر افتاده بازبینی کنید." },
      { name: "پیگیری درخواست توسعه محصول", next: "۸ درخواست توسعه باز مشتری را پیگیری کنید." },
    ],
  },

  /* ---------------------------------------------------------- team */
  team: [
    { name: "محمدحسین صدیقی", role: "علاقه‌مند به یادگیری ماشین با پیشینه نرم‌افزار" },
    { name: "رضا سلطان تویه", role: "علم داده" },
    { name: "حسین ظریف ایمانی", role: "مهندس نرم‌افزار" },
  ],
};
