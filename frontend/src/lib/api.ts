// Real-data API client for the frontend (Dashboard, Customers, Customer 360).
// No mock data — everything is fetched from the DuckDB backend.

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

export interface DashboardData {
  kpis: KpiValue[];
  purchaseTrend: TrendPoint[];
  complaintTrend: TrendPoint[];
  segmentDistribution: DistributionSlice[];
  statusDistribution: DistributionSlice[];
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

export interface RiskSignal {
  label: string;
  tone: "positive" | "negative" | "neutral";
  detail: string;
}

export interface Customer360Data {
  customer: Record<string, unknown>;
  summary: string;
  riskScore: number;
  riskLevel: string;
  riskSignals: RiskSignal[];
  orders: number;
  revenue: number;
  avgOrderValue: number;
  lastPurchase: string | null;
  topProduct: string | null;
  complaints: number;
  complaintReasons: { reason: string; count: number }[];
  collectionsCount: number;
  collectionsAmount: number;
}

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

export async function fetchCustomers(): Promise<CustomerRow[]> {
  const data = await getJson<{ customers: CustomerRow[] }>("/customers");
  return data.customers ?? [];
}

export function fetchCustomer360(id: string): Promise<Customer360Data> {
  return getJson<Customer360Data>(`/customers/${encodeURIComponent(id)}/360`);
}
