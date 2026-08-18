import {
  customers,
  complaintReasons,
  riskTiers,
} from "@/lib/mock-data";
import type { Customer, Kpi } from "@/lib/types";

export type ChartKind = "bar" | "donut";

export interface AgentChart {
  kind: ChartKind;
  title: string;
  data: { name: string; value: number }[];
}

export interface AgentResponse {
  text: string;
  kpis?: Kpi[];
  customers?: Customer[];
  chart?: AgentChart;
}

const highRiskCustomers = customers.filter((c) => c.risk === "high");

function respondAtRisk(): AgentResponse {
  const avgChange =
    highRiskCustomers.reduce((acc, c) => acc + c.purchaseChange, 0) /
    highRiskCustomers.length;
  const atRiskRevenue = highRiskCustomers.reduce((acc, c) => acc + c.revenue, 0);
  const totalComplaints = highRiskCustomers.reduce((acc, c) => acc + c.complaints, 0);

  return {
    text: `I found ${highRiskCustomers.length} customers at high risk, representing $${(
      atRiskRevenue / 1000
    ).toFixed(1)}K in revenue. These accounts show declining purchases (avg. ${avgChange.toFixed(
      1
    )}%) and elevated complaint volume. I'd recommend reaching out within the next week.`,
    kpis: [
      { label: "High Risk Accounts", value: `${highRiskCustomers.length}`, change: "-1.4%", trend: "down" },
      { label: "At-Risk Revenue", value: `$${(atRiskRevenue / 1000).toFixed(1)}K`, change: "-4.2%", trend: "down" },
      { label: "Complaints (High Risk)", value: `${totalComplaints}`, change: "+12%", trend: "up" },
      { label: "Avg. Purchase Change", value: `${avgChange.toFixed(1)}%`, change: "-20.1%", trend: "down" },
    ],
    customers: [...highRiskCustomers].sort((a, b) => a.purchaseChange - b.purchaseChange),
    chart: {
      kind: "donut",
      title: "Risk distribution",
      data: riskTiers.map((t) => ({ name: `${t.tier} risk`, value: t.customers })),
    },
  };
}

function respondReducedPurchases(): AgentResponse {
  const churnSignals = customers.filter(
    (c) => c.complaints >= 4 && c.purchaseChange < 0
  );
  const avgDrop =
    churnSignals.reduce((acc, c) => acc + c.purchaseChange, 0) / churnSignals.length;

  return {
    text: `${churnSignals.length} customers reduced their purchases after filing 4 or more complaints. On average their purchase volume dropped ${Math.abs(
      avgDrop
    ).toFixed(1)}% in the following period — a strong early churn signal.`,
    kpis: [
      { label: "Affected Accounts", value: `${churnSignals.length}`, change: "+3", trend: "up" },
      { label: "Avg. Purchase Drop", value: `${avgDrop.toFixed(1)}%`, change: "-14.2%", trend: "down" },
      { label: "Lost Revenue Est.", value: "$1.1M", change: "-9.5%", trend: "down" },
    ],
    customers: [...churnSignals].sort((a, b) => a.purchaseChange - b.purchaseChange),
  };
}

function respondComplaintReasons(): AgentResponse {
  const total = complaintReasons.reduce((acc, r) => acc + r.count, 0);
  const top = complaintReasons[0];

  return {
    text: `The most common complaint reason is ${top.reason.toLowerCase()} (${top.count} cases). Together, the top three reasons account for ${Math.round(
      ((complaintReasons[0].count + complaintReasons[1].count + complaintReasons[2].count) / total) * 100
    )}% of all complaints. Billing and delivery issues are worth prioritizing first.`,
    kpis: [
      { label: "Total Complaints", value: `${total}`, change: "+4.8%", trend: "up" },
      { label: "Top Reason", value: top.reason, trend: "neutral" },
      { label: "Billing Errors", value: `${top.count}`, change: "+6.2%", trend: "up" },
    ],
    chart: {
      kind: "bar",
      title: "Complaints by reason",
      data: complaintReasons.map((r) => ({ name: r.reason, value: r.count })),
    },
  };
}

export function getAgentResponse(question: string): AgentResponse {
  const q = question.toLowerCase();

  if (q.includes("at risk") || q.includes("risk")) {
    return respondAtRisk();
  }
  if (q.includes("reduced purchases") || q.includes("after complaint") || q.includes("purchase")) {
    return respondReducedPurchases();
  }
  if (q.includes("complaint") && q.includes("reason")) {
    return respondComplaintReasons();
  }
  if (q.includes("complaint")) {
    return respondComplaintReasons();
  }

  return {
    text: "I can help you explore your customer base. Try asking about customers at risk, customers who reduced purchases after complaints, or the main complaint reasons.",
  };
}

export function delayResponse(): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, 900));
}
