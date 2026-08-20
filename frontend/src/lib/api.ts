// Real-data API client for the frontend (Dashboard, Customers, Customer 360,
// Analyses). No mock data — everything is fetched from the DuckDB backend.

export interface KpiValue {
  label: string;
  value: number;
  change?: string | null;
  trend?: "up" | "down" | "neutral" | null;
}

export interface TrendPoint {
  month: string;
  value: number;
}

export interface DistributionSlice {
  name: string;
  value: number;
}

export interface RiskSignal {
  id?: string;
  label: string;
  tone: "positive" | "negative" | "neutral";
  detail: string;
  reasons?: string[];
}

export interface CustomerAction {
  id: string;
  name: string;
  reason: string;
  evidence?: string[];
  next_step?: string;
}

export interface ComplaintRecord {
  id: string;
  date: string | null;
  title: string | null;
  text: string | null;
  severity: string | null;
  status: string | null;
  product: string | null;
}

export interface InteractionRecord {
  id: string;
  date: string | null;
  type: string | null;
  summary: string | null;
  next_action: string | null;
  rep: string | null;
}

export interface TransactionRecord {
  invoice: string;
  date: string | null;
  amount: number;
  lines: number;
}

export interface DevRequestRecord {
  id: string;
  date: string | null;
  type: string | null;
  text: string | null;
  status: string | null;
  owner: string | null;
}

export interface OfferRecord {
  id: string;
  date: string | null;
  type: string | null;
  discount_pct: number | null;
  result: string | null;
  product: string | null;
}

export interface CollectionRecord {
  id: string;
  date: string | null;
  amount: number;
  delay_days: number | null;
  bounced: string | null;
}

export interface MarketSignalRecord {
  date: string | null;
  market: string | null;
  competitor: string | null;
  customer_signal: string | null;
  demand: string | null;
  trend: string | null;
}

export interface Customer360Data {
  customer: Record<string, unknown>;
  customerProfile: { label: string; value: unknown }[];
  summary: string | null;
  summaryReady: boolean;
  riskScore: number | null;
  riskLevel: string;
  riskSignals: RiskSignal[];
  state: Record<string, { status: string; reasons?: string[] }>;
  actions: CustomerAction[];
  orders: number;
  revenue: number;
  avgOrderValue: number;
  lastPurchase: string | null;
  topProduct: string | null;
  complaints: number;
  unresolvedComplaints: number;
  complaintReasons: { reason: string; count: number }[];
  complaintList: ComplaintRecord[];
  interactions: InteractionRecord[];
  interactionsCount: number;
  transactions: TransactionRecord[];
  devRequests: DevRequestRecord[];
  devCount: number;
  devOpen: number;
  offers: OfferRecord[];
  offerAcceptance: number | null;
  bestOfferType: string | null;
  collections: CollectionRecord[];
  collectionsCount: number;
  collectionsAmount: number;
  overdueAmount: number;
  bouncedChecks: number;
  marketSignals: MarketSignalRecord[];
}

export interface DashboardIntelligence {
  at_risk: {
    count: number;
    revenue: number;
    top: {
      customer_id: string;
      complaints: number;
      orders: number;
      revenue: number;
      last_purchase: string | null;
      days_since: number | null;
      bounced: number;
      risk_score: number;
    }[];
  };
  complaint_themes: { name: string; count: number }[];
  offer_effectiveness: { type: string; rate: number; count: number }[];
  collection_risk: { overdue: number; bounced: number };
  winback: { count: number; revenue: number };
  segment_share: { name: string; value: number }[];
}

export interface DashboardData {
  kpis: KpiValue[];
  purchaseTrend: TrendPoint[];
  complaintTrend: TrendPoint[];
  segmentDistribution: DistributionSlice[];
  statusDistribution: DistributionSlice[];
  intelligence: DashboardIntelligence;
  recommendations: IncomeRecommendation[];
}

export interface IncomeRecommendation {
  id: string;
  tone: "negative" | "positive" | "warning";
  title: string;
  detail: string;
  impact: number;
}

export interface AnalysesData {
  atRisk: {
    customer: string;
    segment: string | null;
    status: string | null;
    complaints: number;
    orders: number;
    revenue: number;
    last_purchase: string | null;
    days_since: number | null;
    bounced: number;
    risk_level: string;
  }[];
  complaintThemes: { name: string; count: number }[];
  revenueConcentration: { name: string; value: number; customers: number }[];
  churnFactors: {
    never_bought: number;
    inactive_180_365: number;
    inactive_over_365: number;
    inactive_with_complaints: number;
  };
  incomeRecommendations: IncomeRecommendation[];
}

export type SummaryStatus =
  | { status: "ready"; summary: string; generated: boolean }
  | { status: "generating"; summary: null; generated: boolean }
  | { status: "not_ready"; summary: null; generated: boolean }
  | { status: "not_found"; summary: null; generated: boolean };

// Backend is reached directly at its absolute path (no Vite proxy).
const BACKEND_PORT = Number(import.meta.env.VITE_BACKEND_PORT || 8000);
const API_URL = `http://127.0.0.1:${BACKEND_PORT}/api`;

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(`${API_URL}${path}`);
  if (!res.ok) throw new Error(`Backend returned ${res.status}`);
  return (await res.json()) as T;
}

export function fetchDashboard(): Promise<DashboardData> {
  return getJson<DashboardData>("/dashboard");
}

export function fetchDashboardIntelligence(refresh = false): Promise<SummaryStatus> {
  return getJson<SummaryStatus>(`/dashboard/intelligence${refresh ? "?refresh=1" : ""}`);
}

export function fetchAnalyses(): Promise<AnalysesData> {
  return getJson<AnalysesData>("/analyses");
}

export async function fetchCustomers(): Promise<CustomerRow[]> {
  const data = await getJson<{ customers: CustomerRow[] }>("/customers");
  return data.customers ?? [];
}

export function fetchCustomer360(id: string): Promise<Customer360Data> {
  return getJson<Customer360Data>(`/customers/${encodeURIComponent(id)}/360`);
}

export function fetchCustomer360Summary(id: string, refresh = false): Promise<SummaryStatus> {
  return getJson<SummaryStatus>(
    `/customers/${encodeURIComponent(id)}/360/summary${refresh ? "?refresh=1" : ""}`
  );
}

export interface CustomerRow {
  Customer_ID: string;
  Customer_Segment: string | null;
  Customer_Status: string | null;
  Credit_Limit: number | null;
  Payment_Terms_Days: number | null;
  Relationship_Start_Date: string | null;
  Sales_Rep_ID: string | null;
  orders: number;
  revenue: number;
  complaints: number;
}
