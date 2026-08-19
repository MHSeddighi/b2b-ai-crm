# 1. هدف محصول

ساخت سیستمی که داده‌های پراکنده هر مشتری را به یک تصمیم قابل اقدام برای مدیر فروش تبدیل کند.

مسیر اصلی محصول:

**Data → Current State → Signals → Customer Status → Recommended Action → Evidence**

سیستم نباید فقط بگوید چه اتفاقی افتاده؛ باید بگوید:

1. چه چیزی تغییر کرده؟
2. وضعیت فعلی چیست؟
3. چرا مهم است؟
4. چه کاری باید انجام شود؟
5. این نتیجه بر اساس چه داده‌ای است؟

---

# 2. کاربر اصلی

**Sales Manager / Account Manager**

کاربر باید بتواند در کمتر از چند دقیقه بفهمد:

- کدام مشتری نیاز به توجه دارد؟
- مشکل یا فرصت چیست؟
- آیا مشکل هنوز وجود دارد یا حل شده؟
- مشتری ارزش پیگیری دارد یا نه؟
- الان چه اقدامی باید انجام شود؟

---

# 3. خروجی نهایی هر مشتری

برای هر مشتری سیستم باید یک Object نهایی شبیه این تولید کند:

```json
{
  "customer_id": "CUST-058",
  "status": "Needs Attention",
  "priority": "High",

  "summary": "مشتری ارزشمند است اما خرید در حال کاهش است و اخیراً مشکل کیفیت داشته.",

  "signals": [],
  "recommended_actions": [],
  "evidence": [],
  "confidence": "High"
}
```

---

# 4. تقسیم پروژه

پروژه به 7 ماژول مستقل تقسیم شود:

1. Data & Tool Layer
2. Customer 360
3. Current State Engine
4. Signal Engine
5. Customer Classification
6. Action Engine
7. AI Explanation & Evidence

هر بخش می‌تواند Owner جدا داشته باشد.

---

# MODULE 1 — Data & Tool Layer

## مسئولیت

فرد مسئول این بخش باید تمام Data Sourceها را برای سیستم قابل استفاده کند.

## کارهایی که باید انجام شود

برای هر جدول مشخص شود:

- نام جدول
- کاربرد جدول
- Grain جدول
- Primary Key
- Foreign Keys
- Entityها
- معنی ستون‌ها
- ارتباط با جدول‌های دیگر
- محدودیت‌ها و مشکلات Data Quality
- چه سؤال‌هایی با این جدول قابل پاسخ است

مثلاً:

### فروش

کاربرد:

> فهمیدن اینکه مشتری چه چیزی، چه زمانی، با چه مقدار و چه قیمتی خریده است.

Tool احتمالی:

```text
get_customer_sales(
    customer_id,
    start_date,
    end_date,
    product_id
)
```

خروجی باید Structured باشد.

## Toolهای مورد نیاز

حداقل:

```text
get_customer_profile()
get_customer_sales()
get_customer_invoices()
get_customer_payments()
get_customer_complaints()
get_customer_crm_interactions()
get_customer_offers()
get_customer_wallet_share()
get_customer_development_requests()
get_customer_quality_records()
get_customer_costs()
```

## نکته مهم

LLM نباید مستقیماً SQL آزاد روی تمام دیتابیس بزند.

Toolها بهتر است کنترل‌شده و قابل پیش‌بینی باشند.

## Definition of Done

این بخش تمام شده است اگر:

- برای یک Customer\_ID بتوان تمام داده‌های مرتبط را بازیابی کرد.
- Duplicate Join ایجاد نشود.
- Customer Identity Mapping حل شده باشد.
- هر خروجی Source و Timestamp داشته باشد.

---

# MODULE 2 — Customer 360

## مسئولیت

تبدیل داده‌های مختلف به یک View واحد از مشتری.

## خروجی مورد انتظار

```json
{
  "customer": {},
  "sales": {},
  "payments": {},
  "profitability": {},
  "complaints": {},
  "relationship": {},
  "offers": {},
  "wallet": {},
  "opportunities": {},
  "recent_events": []
}
```

## صفحه UI پیشنهادی

بالای صفحه:

**Customer Name**

سپس:

```text
Current Status
Priority
Real Profit
Purchase Trend
Payment Status
Wallet Share
Relationship Status
```

پایین‌تر:

### Recent Events

مثلاً:

```text
12 Aug — Payment received
8 Aug — CRM meeting
2 Aug — Complaint closed
26 Jul — Order placed
```

## نکته

Customer 360 نباید فقط چند جدول کنار هم باشد.

باید یک **Current Account View** ایجاد کند.

## Definition of Done

با یک API Call:

```text
GET /customer/{id}/360
```

باید View کامل مشتری برگردد.

---

# MODULE 3 — Current State Engine

این بخش بسیار مهم است.

## مسئولیت

تشخیص اینکه یک Event قدیمی هنوز مهم است یا نه.

مثلاً:

```text
Complaint happened
```

کافی نیست.

باید بفهمیم:

```text
Complaint happened
↓
Was it resolved?
↓
Did it repeat?
↓
Did later purchases recover?
↓
Is it still relevant today?
```

## Stateهای پیشنهادی

برای Issueها:

```text
NEW
ACTIVE
IMPROVING
RESOLVED
RECURRING
STALE
```

## مثال Complaint

ورودی:

- Complaint Severity
- Complaint Date
- Resolution
- Lot Quality
- Recent Orders
- New Complaints

خروجی:

```json
{
  "issue": "Quality",
  "state": "RESOLVED",
  "severity": "High",
  "current_relevance": "Low",
  "reason": "شکایت بسته شده و دو خرید بعدی بدون شکایت بوده‌اند."
}
```

## برای چه چیزهایی State بسازیم؟

### Quality

- مشکل هنوز وجود دارد؟
- رفع شده؟
- تکرار شده؟

### Payment

- هنوز بدهکار است؟
- پرداخت کرده؟
- رفتار پرداخت بهتر شده؟

### Purchase Decline

- کاهش ادامه دارد؟
- خرید برگشته؟
- فصلی بوده؟

### Relationship

- رابطه اخیراً بهتر یا بدتر شده؟

### Offer

- Offer هنوز Open است؟
- Accepted؟
- Rejected؟
- Expired؟

## Definition of Done

هر Problem Signal باید علاوه بر History دارای **Current State** باشد.

---

# MODULE 4 — Signal Engine

## مسئولیت

محاسبه Signalها با Code.

LLM نباید Signal اصلی را محاسبه کند.

## Signalهای MVP

### 1. RFM

خروجی:

```text
R
F
M
Previous RFM
Current RFM
Movement
```

مهم‌تر از Score:

```text
5-5-5 → 3-4-5
```

---

### 2. LTV

خروجی:

```text
Estimated Future Value
Confidence
Assumptions
```

برای MVP می‌تواند Formula-based باشد.

---

### 3. Share of Wallet

```text
Our Spend / Estimated Customer Spend
```

خروجی:

```text
Current Wallet Share
Previous Wallet Share
Change
Confidence
Source
```

---

### 4. Real Profit

حداقل:

```text
Revenue
- COGS
- Returns
- Cost of Money
= Real Profit
```

هم Amount و هم Margin نمایش داده شود.

---

### 5. Payment Behaviour

موارد مهم:

```text
Average Delay
Outstanding Balance
Returned Cheques
Trend
```

خروجی مثلاً:

```text
GOOD
WATCH
BAD
```

---

### 6. Relationship Quality

ورودی:

- CRM interactions
- complaints
- offer acceptance
- interaction recency
- unresolved issues

خروجی:

```text
STRONG
NORMAL
WEAKENING
POOR
```

---

### 7. Purchase Trend

مقایسه رفتار مشتری با History خودش.

خروجی:

```text
GROWING
STABLE
DECLINING
RECOVERING
ABNORMAL_DROP
```

---

### 8. Churn Risk

ترکیبی از Signalهای دیگر.

مثلاً:

```text
Purchase Decline
+ Relationship Decline
+ Complaint
+ Offer Rejection
+ Interaction Gap
```

خروجی:

```text
LOW
MEDIUM
HIGH
```

همراه با Reason Codes.

---

### 9. Cross-sell Opportunity

بررسی:

- Product Mix
- Wallet Gap
- Similar Customers
- Development Requests
- Offers
- Profitability
- Payment Behaviour

خروجی:

```json
{
  "product": "Product X",
  "opportunity": "HIGH",
  "reason": "...",
  "blocked_by": []
}
```

## Definition of Done

برای هر مشتری API زیر وجود داشته باشد:

```text
GET /customer/{id}/signals
```

و هر Signal شامل این‌ها باشد:

```text
value
status
trend
reason_codes
evidence_ids
calculated_at
```

---

# MODULE 5 — Customer Classification

هدف این بخش ساده‌کردن 9 Signal برای مدیر فروش است.

به‌جای اصطلاحات پیچیده، پیشنهاد می‌شود فقط 4 وضعیت داشته باشیم.

## 1. رشد بده

مشتری خوب است و ظرفیت رشد دارد.

مثلاً:

```text
Real Profit HIGH
Wallet Share LOW
Payment GOOD
Relationship GOOD
```

→ **رشد بده**

---

## 2. حفظ کن

مشتری ارزشمند است ولی باید مراقب او باشیم.

```text
High Value
High Profit
High Wallet Share
```

→ **حفظ کن**

---

## 3. مشکل را حل کن

مشتری ارزش دارد اما چیزی جلوی رشد را گرفته.

مثلاً:

```text
High Value
Purchase ↓
Complaint Active
```

یا:

```text
Sales High
Payment Bad
Real Profit Low
```

→ **مشکل را حل کن**

---

## 4. کمتر وقت بگذار

```text
Low Profit
Low Potential
Low Wallet Opportunity
High Cost to Serve
```

→ **کمتر وقت بگذار**

## Definition of Done

هر مشتری دقیقاً یک **Primary State** داشته باشد و سیستم توضیح دهد چرا.

---

# MODULE 6 — Action Engine

## مسئولیت

تبدیل وضعیت مشتری به Action مشخص.

Actionها باید محدود و قابل کنترل باشند.

## Action Catalog

### Relationship

```text
CALL_CUSTOMER
SCHEDULE_MEETING
CHECK_SATISFACTION
ESCALATE_ACCOUNT
```

### Quality

```text
FOLLOW_UP_COMPLAINT
QUALITY_REVIEW_MEETING
SEND_QUALITY_REPORT
```

### Sales

```text
CROSS_SELL_PRODUCT
UPSELL_PRODUCT
SEND_OFFER
RENEW_OFFER
```

### Commercial

```text
RENEGOTIATE_PRICE
RENEGOTIATE_PAYMENT_TERMS
REDUCE_DISCOUNT
```

### Collection

```text
FOLLOW_UP_PAYMENT
REVIEW_CREDIT_LIMIT
BLOCK_NEW_CREDIT_OFFER
```

### Attention

```text
INCREASE_ATTENTION
MAINTAIN_ATTENTION
REDUCE_ATTENTION
```

---

# Action Rules

مثلاً:

```text
IF
Churn Risk = HIGH
AND LTV = HIGH
AND Complaint State = ACTIVE

THEN
QUALITY_REVIEW_MEETING
```

---

```text
IF
Wallet Share = LOW
AND Real Profit = HIGH
AND Payment = GOOD
AND Relationship != POOR

THEN
CROSS_SELL_PRODUCT
```

---

```text
IF
Cross Sell = HIGH
BUT Payment = BAD

THEN
FOLLOW_UP_PAYMENT

NOT
SEND_OFFER
```

این قسمت بسیار مهم است:

**Opportunity ≠ Action**

Constraintها باید قبل از Action بررسی شوند.

---

# Action Object

```json
{
  "action": "SCHEDULE_MEETING",
  "priority": "HIGH",
  "owner": "Account Manager",
  "reason_codes": [
    "PURCHASE_DECLINE",
    "ACTIVE_QUALITY_ISSUE",
    "HIGH_LTV"
  ],
  "objective": "رفع مشکل کیفیت و بازیابی حجم خرید"
}
```

---

# MODULE 7 — AI Explanation & Evidence Layer

## مسئولیت LLM

LLM قرار نیست تصمیم مالی محاسبه کند.

وظایفش:

### 1. خلاصه کردن Customer 360

مثلاً:

> مشتری همچنان سودآور است، اما خرید سه ماه اخیر ۲۸٪ کاهش یافته است.

### 2. خواندن متن CRM و Complaint

استخراج:

```text
Problem
Cause
Sentiment
Commitment
Next step
```

### 3. توضیح Signalها

### 4. توضیح Action

مثلاً:

> جلسه بررسی کیفیت پیشنهاد شده زیرا افت خرید بعد از دو شکایت کیفی شروع شده و آخرین شکایت هنوز باز است. مشتری همچنان LTV بالایی دارد.

---

# Evidence

هر Claim باید Evidence داشته باشد.

مثلاً UI:

**Why this action?**

> Purchase ↓ 28%\
> Quality complaint still active\
> Customer LTV: High\
> Real Profit: 11.8%

**View evidence →**

سپس رکوردهای واقعی باز شوند.

## Definition of Done

LLM نباید عدد جدید اختراع کند.

تمام عددها باید از Signal Engine یا Data Tools وارد Prompt شوند.

---

# 5. Contract بین تمام تیم‌ها

همه Moduleها باید حول یک Customer ID مشترک کار کنند.

Flow:

```text
Customer_ID
    ↓
Customer 360
    ↓
Current States
    ↓
Signals
    ↓
Classification
    ↓
Actions
    ↓
LLM Explanation
    ↓
Evidence
```

---

# 6. چیزی که در UI باید دیده شود

صفحه اصلی می‌تواند لیست مشتریان باشد:

| Customer | وضعیت          | Priority | مشکل/فرصت     | Action           |
| -------- | -------------- | -------- | ------------- | ---------------- |
| A        | رشد بده        | High     | Wallet gap    | Cross-sell       |
| B        | مشکل را حل کن  | High     | Late payment  | Payment meeting  |
| C        | حفظ کن         | Medium   | Stable        | Monitor          |
| D        | کمتر وقت بگذار | Low      | Low potential | Reduce attention |

با کلیک روی مشتری:

## Customer 360

سپس:

### Why now?

سه Signal مهم.

### Current situation

مشکلات Open / Resolved.

### Recommended Action

یک Action اصلی.

### Why?

Evidence.

---

# 7. Demo Scenario پیشنهادی

برای Demo بهتر است یک مشتری انتخاب شود که Story جذابی داشته باشد:

```text
مشتری قبلاً خوب بوده
↓
خرید کاهش یافته
↓
شکایت کیفیت ثبت شده
↓
بررسی Current State
↓
مشکل هنوز Active است
↓
Real Profit همچنان خوب است
↓
LTV بالا است
↓
نباید مشتری را رها کرد
↓
System = "مشکل را حل کن"
↓
Action = جلسه کیفیت
↓
Evidence نمایش داده شود
```

و مشتری دوم:

```text
Wallet Share پایین
+ Profit بالا
+ Payment خوب
+ Relationship خوب
↓
"رشد بده"
↓
Cross-sell Product X
```

با همین دو Case تقریباً تمام ارزش محصول قابل نمایش است.

---

# 8. تقسیم پیشنهادی بین اعضای تیم

## Person 1 — Data

مسئول:

- Metadata
- Relationships
- Identity Resolution
- Database
- Tool Functions

تحویل:

**Customer Data API**

---

## Person 2 — Analytics

مسئول:

- RFM
- Real Profit
- Payment
- Wallet
- Purchase Trend
- LTV

تحویل:

**Signal Engine**

---

## Person 3 — Decision Engine

مسئول:

- Current State
- Churn
- Relationship
- Cross-sell
- Classification
- Action Rules

تحویل:

**Decision API**

---

## Person 4 — AI

مسئول:

- Complaint Extraction
- CRM Text Extraction
- Customer Summary
- Explanation
- Evidence Grounding

تحویل:

**AI Synthesis Layer**

---

## Person 5 — Frontend

مسئول:

- Customer list
- Customer 360
- Signals
- Recommended Action
- Evidence Drill-down

تحویل:

**Demo Application**

اگر اعضای تیم کمتر هستند، Data + Analytics و Decision + AI را ادغام کنید.

---

# 9. قانون اصلی محصول

هیچ Action نباید فقط به دلیل وجود یک Event صادر شود.

همیشه:

```text
Historical Event
+
Current State
+
Customer Value
+
Commercial Context
+
Constraints
=
Action
```

مثلاً:

```text
Complaint exists
```

→ به تنهایی Action نیست.

اما:

```text
Complaint ACTIVE
+
Purchase declining
+
Real Profit high
+
LTV high
```

→

**جلسه بررسی کیفیت با اولویت بالا**

---

# 01. Definition of Success

MVP موفق است اگر مدیر فروش بتواند روی یک مشتری کلیک کند و در کمتر از 30 ثانیه بفهمد:

> این مشتری چه وضعیتی دارد؟

> چه چیزی تغییر کرده؟

> آیا مشکل هنوز وجود دارد؟

> چرا برای من مهم است؟

> الان دقیقاً چه کاری باید انجام دهم؟

> سیستم بر چه اساسی این حرف را می‌زند؟

اگر این شش سؤال جواب داده شوند، محصول هسته اصلی مسئله هکاتون را حل کرده است.
