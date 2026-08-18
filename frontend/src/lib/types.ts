export type RiskLevel = "high" | "medium" | "low";

export type Segment = "Enterprise" | "Mid-Market" | "SMB";

export interface Customer {
  id: string;
  name: string;
  company: string;
  segment: Segment;
  revenue: number;
  complaints: number;
  purchaseChange: number; // percent vs prior period
  risk: RiskLevel;
  accountOwner: string;
  region: string;
  lastPurchase: string;
}

export interface TrendPoint {
  month: string;
  value: number;
}

export interface ComplaintReason {
  reason: string;
  count: number;
}

export interface RiskTier {
  tier: string;
  customers: number;
  revenue: number;
}

export interface Kpi {
  label: string;
  value: string;
  change?: string;
  trend?: "up" | "down" | "neutral";
  icon?: string;
}
