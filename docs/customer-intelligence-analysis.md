# Customer Intelligence Analysis

This document defines the analytical layer built on top of the Customer 360 system.

Before implementing any risk, complaint, or sales-opportunity feature, read this document first.

The goal is to build a simple, explainable, data-driven Customer Intelligence layer. Do not introduce unnecessarily complex ML models unless the actual dataset proves they are needed.

---

The Customer 360 layer connects records from different sources to canonical customers.

The Customer Intelligence layer uses that unified data to answer the main questions **at the customer level**:

1. Which customers are at risk?
2. What relationship exists between complaints and purchasing behavior?
3. Where are the sales opportunities through upselling and cross-selling?

The main capabilities are:

```text
Customer 360
     │
     ▼
Customer Intelligence
     │
     ├── Customer Risk
     │
     ├── Complaint ↔ Purchase Analysis
     │
     └── Sales Opportunities
           ├── Upsell
           └── Cross-sell
```

---

# 1. Customer Risk Analysis

## Goal

Identify customers showing signals of potential churn, declining engagement, or deteriorating customer relationships.

The first version should use an explainable scoring system rather than a complex predictive ML model.

## Signals

### Purchase behavior

Use available signals such as:

* revenue trend
* quantity trend
* purchase frequency
* days since last purchase
* change in average order value
* change in purchase frequency
* historical purchase level

### Complaint behavior

Use:

* complaint count
* recent complaint count
* complaint frequency
* quality-related complaints
* unresolved complaints
* complaint severity if available

### CRM / interaction signals

Use available information such as:

* recent interactions
* interaction frequency
* negative/critical notes
* inactivity

Do not assume a signal exists. Inspect the actual dataset first.

---

## Risk Score

Create a transparent risk score from relevant signals.

Conceptually:

```text
Risk Score
    =
    Purchase deterioration
    +
    Recency
    +
    Complaint signals
    +
    CRM/interaction signals
```

The exact weights should be configurable and should be based on the available data.

Example:

```text
Customer X

Risk Score: 84 / 100
Risk Level: HIGH

Purchase trend:       -32%
Complaint trend:      +45%
Last purchase:        47 days ago
Quality complaints:   3

Main risk signals:
- Significant purchase decline
- Increasing complaints
- Recent quality-related complaints
```

The score must be explainable.

The system should be able to show which signals contributed to the risk.

Do not claim that the customer will definitely churn.

Use language such as:

* "high risk"
* "shows signs of decline"
* "potential churn risk"
* "requires attention"

rather than deterministic statements.

---

# 2. Complaint ↔ Purchase Analysis

## Goal

Discover whether customer purchasing behavior changes around complaint events.

The main question is:

> "What happens to a customer's purchasing behavior before and after a complaint, especially a quality-related complaint?"

This is an observational analysis.

Do NOT claim causality unless a proper causal methodology is explicitly implemented.

---

## Analysis Method

For each complaint:

```text
Complaint
   │
   ├── Customer
   ├── Complaint Type
   ├── Severity
   └── Date
          │
          ▼
   Purchase behavior
          │
     ┌────┴────┐
     ▼         ▼
   Before     After
   window     window
```

Compare metrics such as:

* revenue
* quantity
* order count
* purchase frequency
* average order value

For example:

```text
Customer X

3 months before complaint:
Revenue: 1.2B
Orders: 8
Quantity: 420

3 months after complaint:
Revenue: 760M
Orders: 5
Quantity: 270

Revenue change: -36.7%
Quantity change: -35.7%
```

The time window must be configurable.

Possible default:

```text
Before: 90 days
After: 90 days
```

Only use a window that makes sense for the actual transaction frequency.

---

# 3. Quality Complaint Analysis

Quality complaints should receive special attention.

Analyze, at the customer level:

```text
Quality Complaint
       │
       ▼
Affected Customer
       │
       ▼
Purchase Before / After
```

Calculate:

* number of quality complaints
* affected customers
* purchase change after complaint
* percentage of affected customers showing purchase decline

Example:

```text
Quality complaints:       23
Affected customers:       18
Customers with decline:   12

Average purchase change:
-21%
```

The system should report this as an observed association.

Example:

> "Customers who experienced quality-related complaints showed an average 21% decline in purchase volume afterward."

Do NOT state:

> "Quality complaints caused a 21% decline."

unless a valid causal analysis has been performed.

---

# 4. Sales Opportunities

The system should identify two types of sales opportunities:

```text
Sales Opportunities
       │
       ├── Upsell
       └── Cross-sell
```

These are opportunity signals, not guaranteed sales forecasts.

---

# 5. Upsell Analysis

## Goal

Identify customers who may have potential to purchase more of products they already buy.

Useful signals include:

* current purchase volume
* historical maximum purchase volume
* recent growth
* purchase frequency
* customer value
* recent engagement
* historical purchasing patterns

Example:

```text
Customer X

Product A:
Current monthly volume:   100
Historical peak:          180
Recent trend:             +15%

Similar/high-value customer behavior:
Average:                  160

Upsell opportunity:       HIGH
```

Create an explainable Upsell Score.

Conceptually:

```text
Upsell Score
    =
    Historical purchase gap
    +
    Recent growth
    +
    Customer value
    +
    Purchase frequency
```

Only use signals supported by the actual data.

---

# 6. Cross-sell Analysis

## Goal

Identify customers who purchase one product but may have an opportunity to purchase another related product.

Start by discovering product relationships from transaction data.

Useful metrics:

* co-purchase count
* support
* confidence
* lift

Example:

```text
Product A → Product B

Customers buying A:       500
Customers buying A + B:   220

P(B | A) = 44%
```

Then find customers who:

```text
buy A
+
do not buy B
+
have sufficient purchase activity
```

Example:

```text
Customer X

Product A: ✓
Product B: ✗

A → B relationship: strong

Cross-sell opportunity: HIGH
```

Avoid recommending products solely because they are globally popular.

Recommendations should be based on observed purchasing relationships.

---

# 7. Opportunity Scoring

Both upsell and cross-sell opportunities should have an explainable score.

Potential signals:

### Upsell

* historical purchase gap
* recent growth
* customer value
* frequency
* recency

### Cross-sell

* product association strength
* customer purchase frequency
* customer value
* number of related products already purchased
* recency

Example:

```text
Opportunity Score: 87 / 100

Type: Cross-sell

Customer: X
Current product: A
Recommended product: B

Why:
- Strong A → B relationship
- Customer frequently purchases A
- Customer has not purchased B
- Customer is highly active
```

---

# 8. Important Analytical Principle

The analytical layer should NOT rely on the LLM to calculate these metrics.

Implement deterministic analytical functions.

Conceptually:

```text
calculate_customer_risk()
analyze_complaint_purchase()
find_upsell_opportunities()
find_cross_sell_opportunities()
```

The LLM should act as an orchestration and explanation layer.

Architecture:

```text
User
  │
  ▼
AI Copilot
  │
  ▼
Intent Detection
  │
  ▼
Analytical Function
  │
  ▼
Structured Result
  │
  ▼
LLM Explanation
  │
  ▼
Dashboard
```

For example:

```text
User:
"کدوم مشتری‌های با ارزش بالا در معرض ریزش هستند؟"

        ↓

LLM identifies:
customer_risk

        ↓

calculate_customer_risk()

        ↓

Structured result

        ↓

LLM explains result

        ↓

Customer table + risk indicators
```

---

# 9. Structured Analytical Output

Analytical functions should return structured data rather than natural-language responses.

For example:

```text
{
    "customer_id": "...",
    "risk_score": 84,
    "risk_level": "high",
    "signals": [
        {
            "name": "purchase_decline",
            "value": -0.32,
            "contribution": 0.40
        },
        {
            "name": "complaint_increase",
            "value": 0.45,
            "contribution": 0.25
        }
    ]
}
```

For opportunities:

```text
{
    "customer_id": "...",
    "type": "cross_sell",
    "current_product": "...",
    "recommended_product": "...",
    "score": 87,
    "reasons": [
        "strong product association",
        "customer frequently purchases current product",
        "customer does not currently purchase recommended product"
    ]
}
```

The frontend can then render:

* KPI cards
* tables
* charts
* badges
* explanations
* recommendations

---

# 10. Recommended MVP Scope

Do NOT implement every possible analysis.

The MVP should contain:

## Customer Risk

```text
Purchase behavior
+
Complaint behavior
+
Recency
→
Explainable Risk Score
```

## Complaint / Purchase

```text
Complaint
→
Before vs After purchase behavior
→
Observed change
```

## Upsell

```text
Existing product
+
Historical/current purchasing behavior
→
Upsell opportunity
```

## Cross-sell

```text
Product associations
+
Customer purchase history
→
Cross-sell opportunity
```

These four analytical capabilities are sufficient for the initial Customer Intelligence MVP.

---

# 11. What NOT to Build Initially

Do not introduce unless the data requires it:

* complex churn prediction models
* deep learning risk models
* causal inference pipelines
* graph neural networks
* complicated product recommendation systems
* reinforcement learning
* complex optimization
* multi-agent systems

Start with transparent statistical/analytical methods.

If the EDA later shows sufficient labeled historical data, more advanced predictive models can be added.

---

# 12. Copilot Questions

The analytical layer should support questions such as:

### Risk

"Which high-value customers are at risk?"

"Why is Customer X considered high risk?"

"Show customers whose purchases are declining while complaints are increasing."

### Complaint / Purchase

"Which quality complaints are associated with purchase declines?"

"How much did purchases change after complaints?"

"Which customers reduced purchases after a quality complaint?"

### Upsell

"Which customers have potential to increase purchases of products they already buy?"

"Which customers have reduced purchases compared with their historical peak?"

### Cross-sell

"Customers who buy Product A but not Product B?"

"Which products are commonly purchased together?"

"Give me the strongest cross-sell opportunities."

---

# Final Architecture

The complete Customer Intelligence layer should follow:

```text
                    Customer 360
                         │
        ┌────────────────┼────────────────┐
        │                │                │
        ▼                ▼                ▼
    Customers        Purchases        Complaints
        │                │                │
        └────────────────┼────────────────┘
                         │
                         ▼
              Customer Intelligence
                         │
       ┌─────────────────┼─────────────────┐
       │                 │                 │
       ▼                 ▼                 ▼
 Customer Risk    Complaint/Purchase   Sales Opportunities
   Analysis           Analysis              │
                         │             ┌─────┴─────┐
                         │             ▼           ▼
                         │          Upsell     Cross-sell
                         │
                         ▼
                    AI Copilot
```

The design principle is:

> **Customer 360 tells us what happened to a customer. Customer Intelligence tells us what it might mean and what action could be taken.**
