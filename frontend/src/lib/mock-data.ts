import type {
  Customer,
  TrendPoint,
  ComplaintReason,
  RiskTier,
  Kpi,
} from "./types";

export const customers: Customer[] = [
  { id: "c1", name: "Acme Corp", company: "Acme Corporation", segment: "Enterprise", revenue: 482000, complaints: 2, purchaseChange: 12.4, risk: "low", accountOwner: "Sara Lee", region: "North America", lastPurchase: "2026-08-02" },
  { id: "c2", name: "Globex", company: "Globex Industries", segment: "Enterprise", revenue: 628000, complaints: 7, purchaseChange: -18.2, risk: "high", accountOwner: "Mike Ross", region: "EMEA", lastPurchase: "2026-05-18" },
  { id: "c3", name: "Initech", company: "Initech Solutions", segment: "Mid-Market", revenue: 142000, complaints: 3, purchaseChange: 4.1, risk: "low", accountOwner: "Priya Patel", region: "North America", lastPurchase: "2026-07-29" },
  { id: "c4", name: "Umbrella Corp", company: "Umbrella Holdings", segment: "Enterprise", revenue: 395000, complaints: 5, purchaseChange: -9.6, risk: "medium", accountOwner: "Tom Nguyen", region: "APAC", lastPurchase: "2026-06-11" },
  { id: "c5", name: "Soylent", company: "Soylent Manufacturing", segment: "Mid-Market", revenue: 218000, complaints: 6, purchaseChange: -22.8, risk: "high", accountOwner: "Sara Lee", region: "EMEA", lastPurchase: "2026-04-30" },
  { id: "c6", name: "Hooli", company: "Hooli Tech", segment: "Enterprise", revenue: 754000, complaints: 1, purchaseChange: 18.7, risk: "low", accountOwner: "Alex Kim", region: "North America", lastPurchase: "2026-08-08" },
  { id: "c7", name: "Stark Industries", company: "Stark Industries", segment: "Enterprise", revenue: 531000, complaints: 4, purchaseChange: -6.3, risk: "medium", accountOwner: "Mike Ross", region: "North America", lastPurchase: "2026-06-25" },
  { id: "c8", name: "Wayne Enterprises", company: "Wayne Enterprises", segment: "Enterprise", revenue: 689000, complaints: 3, purchaseChange: 3.9, risk: "low", accountOwner: "Priya Patel", region: "North America", lastPurchase: "2026-07-15" },
  { id: "c9", name: "Pied Piper", company: "Pied Piper Software", segment: "Mid-Market", revenue: 176000, complaints: 8, purchaseChange: -31.4, risk: "high", accountOwner: "Tom Nguyen", region: "APAC", lastPurchase: "2026-03-22" },
  { id: "c10", name: "Massive Dynamic", company: "Massive Dynamic", segment: "Enterprise", revenue: 472000, complaints: 2, purchaseChange: 7.2, risk: "low", accountOwner: "Sara Lee", region: "EMEA", lastPurchase: "2026-08-01" },
  { id: "c11", name: "Vandelay", company: "Vandelay Industries", segment: "SMB", revenue: 64000, complaints: 4, purchaseChange: -11.9, risk: "medium", accountOwner: "Alex Kim", region: "North America", lastPurchase: "2026-06-03" },
  { id: "c12", name: "Cyberdyne", company: "Cyberdyne Systems", segment: "Enterprise", revenue: 603000, complaints: 6, purchaseChange: -14.5, risk: "high", accountOwner: "Mike Ross", region: "North America", lastPurchase: "2026-05-02" },
  { id: "c13", name: "Tyrell Corp", company: "Tyrell Corporation", segment: "Mid-Market", revenue: 198000, complaints: 1, purchaseChange: 9.3, risk: "low", accountOwner: "Priya Patel", region: "APAC", lastPurchase: "2026-07-22" },
  { id: "c14", name: "Oscorp", company: "Oscorp Industries", segment: "Mid-Market", revenue: 154000, complaints: 5, purchaseChange: -16.1, risk: "high", accountOwner: "Tom Nguyen", region: "EMEA", lastPurchase: "2026-04-14" },
  { id: "c15", name: "Genco Pura", company: "Genco Pura Coffee", segment: "SMB", revenue: 41000, complaints: 2, purchaseChange: 2.4, risk: "low", accountOwner: "Alex Kim", region: "North America", lastPurchase: "2026-07-05" },
  { id: "c16", name: "Nakatomi", company: "Nakatomi Trading", segment: "SMB", revenue: 53000, complaints: 3, purchaseChange: -8.7, risk: "medium", accountOwner: "Sara Lee", region: "APAC", lastPurchase: "2026-06-19" },
  { id: "c17", name: "Gringotts", company: "Gringotts Financial", segment: "Enterprise", revenue: 512000, complaints: 2, purchaseChange: 5.8, risk: "low", accountOwner: "Mike Ross", region: "EMEA", lastPurchase: "2026-08-05" },
  { id: "c18", name: "Wonka", company: "Wonka Industries", segment: "Mid-Market", revenue: 167000, complaints: 7, purchaseChange: -24.2, risk: "high", accountOwner: "Priya Patel", region: "North America", lastPurchase: "2026-03-30" },
  { id: "c19", name: "Weyland", company: "Weyland Corp", segment: "Enterprise", revenue: 458000, complaints: 4, purchaseChange: -5.4, risk: "medium", accountOwner: "Tom Nguyen", region: "APAC", lastPurchase: "2026-06-08" },
  { id: "c20", name: "Durant", company: "Durant Automotive", segment: "SMB", revenue: 72000, complaints: 1, purchaseChange: 11.2, risk: "low", accountOwner: "Alex Kim", region: "North America", lastPurchase: "2026-07-28" },
];

export const purchaseTrend: TrendPoint[] = [
  { month: "Jan", value: 3.1 },
  { month: "Feb", value: 3.4 },
  { month: "Mar", value: 3.2 },
  { month: "Apr", value: 3.7 },
  { month: "May", value: 3.5 },
  { month: "Jun", value: 4.0 },
  { month: "Jul", value: 4.3 },
  { month: "Aug", value: 4.6 },
];

export const complaintTrend: TrendPoint[] = [
  { month: "Jan", value: 34 },
  { month: "Feb", value: 41 },
  { month: "Mar", value: 38 },
  { month: "Apr", value: 52 },
  { month: "May", value: 47 },
  { month: "Jun", value: 58 },
  { month: "Jul", value: 51 },
  { month: "Aug", value: 45 },
];

export const complaintReasons: ComplaintReason[] = [
  { reason: "Billing errors", count: 96 },
  { reason: "Delivery delays", count: 74 },
  { reason: "Product quality", count: 61 },
  { reason: "Support response time", count: 55 },
  { reason: "Feature gaps", count: 38 },
  { reason: "Pricing", count: 24 },
];

export const riskTiers: RiskTier[] = [
  { tier: "Low", customers: 9, revenue: 3.4 },
  { tier: "Medium", customers: 6, revenue: 1.9 },
  { tier: "High", customers: 5, revenue: 1.7 },
];

export const dashboardKpis: Kpi[] = [
  { label: "Total Customers", value: "1,284", change: "+3.2%", trend: "up" },
  { label: "Customers At Risk", value: "87", change: "-1.4%", trend: "down" },
  { label: "Complaints", value: "124", change: "+4.8%", trend: "up" },
  { label: "Revenue", value: "$5.2M", change: "+6.1%", trend: "up" },
];

export const suggestedQuestions: string[] = [
  "Which customers are at risk?",
  "Which customers reduced purchases after complaints?",
  "What are the main complaint reasons?",
];

export const riskColor: Record<Customer["risk"], { text: string; bg: string; dot: string; label: string }> = {
  high: { text: "text-red-600 dark:text-red-400", bg: "bg-red-500/10", dot: "bg-red-500", label: "High" },
  medium: { text: "text-amber-600 dark:text-amber-400", bg: "bg-amber-500/10", dot: "bg-amber-500", label: "Medium" },
  low: { text: "text-emerald-600 dark:text-emerald-400", bg: "bg-emerald-500/10", dot: "bg-emerald-500", label: "Low" },
};
