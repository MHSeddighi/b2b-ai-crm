import type { Customer } from "./types";
import { formatCurrency } from "./utils";

export interface RiskSignal {
  label: string;
  detail: string;
  tone: "positive" | "negative" | "neutral";
}

export interface Opportunity {
  type: "upsell" | "cross-sell";
  title: string;
  detail: string;
  score: number;
}

export interface ActivityItem {
  date: string;
  type: string;
  detail: string;
}

export interface Customer360 {
  summary: string;
  riskScore: number;
  riskSignals: RiskSignal[];
  orders: number;
  avgOrderValue: number;
  topProduct: string;
  purchaseFrequency: string;
  qualityComplaints: number;
  complaintReasons: { reason: string; count: number }[];
  opportunities: Opportunity[];
  activity: ActivityItem[];
}

const products = [
  { name: "Analytics Suite", related: "CRM Pro" },
  { name: "CRM Pro", related: "Support Desk" },
  { name: "Data Platform", related: "Analytics Suite" },
  { name: "Support Desk", related: "Insights API" },
  { name: "Insights API", related: "Data Platform" },
];

const complaintReasonPool = [
  "Product quality",
  "Billing errors",
  "Delivery delays",
  "Support response time",
  "Feature gaps",
];

const TODAY = new Date("2026-08-15T00:00:00Z");

function hash(str: string): number {
  let h = 0;
  for (let i = 0; i < str.length; i++) {
    h = (h * 31 + str.charCodeAt(i)) >>> 0;
  }
  return h;
}

function daysSince(dateStr: string): number {
  const d = new Date(dateStr);
  return Math.max(0, Math.round((TODAY.getTime() - d.getTime()) / 86400000));
}

export function getCustomer360(customer: Customer): Customer360 {
  const h = hash(customer.id);
  const product = products[h % products.length];

  const avgOrderValueBySegment: Record<Customer["segment"], number> = {
    Enterprise: 42000,
    "Mid-Market": 17000,
    SMB: 8000,
  };
  const avgOrderValue = Math.round(
    avgOrderValueBySegment[customer.segment] * (0.9 + (h % 5) * 0.05)
  );
  const orders = Math.max(1, Math.round(customer.revenue / avgOrderValue));

  const riskBase = customer.risk === "high" ? 74 : customer.risk === "medium" ? 45 : 12;
  const riskScore = Math.min(99, riskBase + (h % 18));

  const qualityComplaints = Math.max(
    0,
    Math.round(customer.complaints * (0.4 + (h % 3) * 0.1))
  );

  const purchaseFrequency =
    orders >= 24 ? "Weekly" : orders >= 12 ? "Bi-weekly" : orders >= 4 ? "Monthly" : "Quarterly";

  const pct = customer.purchaseChange;

  // Explainable risk signals
  const riskSignals: RiskSignal[] = [];
  if (pct < -15) {
    riskSignals.push({
      label: "Purchase decline",
      detail: `Purchases down ${Math.abs(pct).toFixed(1)}% vs prior period`,
      tone: "negative",
    });
  } else if (pct < -5) {
    riskSignals.push({
      label: "Purchase softening",
      detail: `Purchases down ${Math.abs(pct).toFixed(1)}% vs prior period`,
      tone: "negative",
    });
  } else {
    riskSignals.push({
      label: "Purchase growth",
      detail: `Purchases up ${pct.toFixed(1)}% vs prior period`,
      tone: "positive",
    });
  }

  if (customer.complaints >= 5) {
    riskSignals.push({
      label: "Complaint load",
      detail: `${customer.complaints} complaints in the current window`,
      tone: "negative",
    });
  } else if (customer.complaints >= 3) {
    riskSignals.push({
      label: "Complaints",
      detail: `${customer.complaints} complaints logged`,
      tone: "neutral",
    });
  } else {
    riskSignals.push({
      label: "Low complaints",
      detail: `Only ${customer.complaints} complaint${customer.complaints === 1 ? "" : "s"}`,
      tone: "positive",
    });
  }

  const since = daysSince(customer.lastPurchase);
  if (since > 60) {
    riskSignals.push({ label: "Recency", detail: `Last purchase ${since} days ago`, tone: "negative" });
  } else if (since > 30) {
    riskSignals.push({ label: "Recency", detail: `Last purchase ${since} days ago`, tone: "neutral" });
  } else {
    riskSignals.push({ label: "Recency", detail: `Last purchase ${since} days ago`, tone: "positive" });
  }

  // Complaint reasons
  const complaintReasons: { reason: string; count: number }[] = [];
  if (customer.complaints > 0) {
    let remaining = customer.complaints;
    const buckets = Math.min(3, customer.complaints);
    for (let i = 0; i < buckets; i++) {
      const count =
        i === buckets - 1 ? remaining : Math.max(1, Math.round(customer.complaints / buckets));
      complaintReasons.push({
        reason: complaintReasonPool[(h + i) % complaintReasonPool.length],
        count,
      });
      remaining -= count;
    }
  }

  // Opportunities
  const opportunities: Opportunity[] = [];
  if (customer.purchaseChange < 5 || customer.revenue < 200000) {
    opportunities.push({
      type: "upsell",
      title: `Upsell ${product.name}`,
      detail: `${customer.name} is below its historical peak for ${product.name}; there is room to expand volume.`,
      score: Math.min(99, 55 + (h % 35)),
    });
  } else {
    opportunities.push({
      type: "upsell",
      title: `Expand ${product.name}`,
      detail: `A growing account — consider increasing adoption of ${product.name}.`,
      score: Math.min(99, 40 + (h % 30)),
    });
  }
  opportunities.push({
    type: "cross-sell",
    title: `${product.name} → ${product.related}`,
    detail: `Customers who buy ${product.name} frequently also buy ${product.related}.`,
    score: Math.min(99, 60 + (h % 30)),
  });

  // Recent activity
  const activity: ActivityItem[] = [];
  const activityDefs = [
    { type: "Purchase", detail: `Order confirmed for ${product.name}` },
    { type: "CRM interaction", detail: `Call logged by ${customer.accountOwner}` },
    {
      type: customer.complaints > 0 ? "Complaint" : "Support",
      detail:
        customer.complaints > 0
          ? `Complaint received — ${complaintReasonPool[h % complaintReasonPool.length].toLowerCase()}`
          : "Support ticket resolved",
    },
    { type: "Sales report", detail: `Account review prepared by ${customer.accountOwner}` },
  ];
  const offsets = [3, 9, 21, 34];
  activityDefs.forEach((def, i) => {
    const d = new Date(TODAY.getTime() - offsets[i] * 86400000);
    activity.push({ date: d.toISOString().slice(0, 10), type: def.type, detail: def.detail });
  });

  // Intelligent summary
  const trendWord = pct >= 0 ? "up" : "down";
  const qualityNote = qualityComplaints > 0 ? `, including ${qualityComplaints} quality-related` : "";
  let action: string;
  if (customer.risk === "high") {
    action = `This account is flagged HIGH risk and needs attention — review recent complaints and re-engage ${customer.accountOwner} before the next purchase cycle.`;
  } else if (customer.risk === "medium") {
    action =
      "The account is stable but shows early warning signs; monitor complaint trends and purchase recency closely.";
  } else {
    action =
      "The account is healthy with low churn risk and is a strong candidate for expansion.";
  }
  const complaintWord = `${customer.complaints} complaint${customer.complaints === 1 ? "" : "s"}`;
  const summary = `${customer.name} (${customer.segment}, ${customer.region}) holds ${formatCurrency(
    customer.revenue
  )} in trailing revenue and a ${customer.risk} risk profile (score ${riskScore}/100). Purchases are ${trendWord} ${Math.abs(
    pct
  ).toFixed(1)}% versus the prior period, with ${complaintWord}${qualityNote}. ${action}`;

  return {
    summary,
    riskScore,
    riskSignals,
    orders,
    avgOrderValue,
    topProduct: product.name,
    purchaseFrequency,
    qualityComplaints,
    complaintReasons,
    opportunities,
    activity,
  };
}
