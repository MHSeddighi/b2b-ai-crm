import { MessageSquareWarning, ShieldAlert, TrendingUp } from "lucide-react";
import type { LucideIcon } from "lucide-react";

import { getAgentResponse, type AgentResponse } from "@/lib/agent";
import { customers } from "@/lib/mock-data";
import type { Message } from "@/components/copilot";

export interface CopilotScenario {
  id: string;
  title: string;
  description: string;
  icon: LucideIcon;
  messages: Message[];
}

let seq = 100;

function user(content: string): Message {
  return { id: `s-u${seq++}`, role: "user", content };
}

function agent(response: AgentResponse): Message {
  return { id: `s-a${seq++}`, role: "agent", response };
}

function upsellResponse(): AgentResponse {
  const candidates = customers
    .filter((c) => c.purchaseChange < 0)
    .sort((a, b) => a.purchaseChange - b.purchaseChange)
    .slice(0, 5);
  return {
    text: `I shortlisted 5 high-value accounts whose purchases are below their historical peak — the strongest upsell candidates right now.`,
    kpis: [
      { label: "Upsell Candidates", value: `${candidates.length}`, change: "+2", trend: "up" },
      { label: "Avg. Purchase Change", value: "-14.3%", trend: "down" },
      { label: "Potential Upsell Revenue", value: "$840K", trend: "up" },
    ],
    customers: candidates,
  };
}

function crossSellResponse(): AgentResponse {
  return {
    text: `From co-purchase patterns, Analytics Suite and CRM Pro are bought together by 44% of Analytics customers (lift 2.3×). The strongest cross-sell targets are active Analytics-only accounts that haven't adopted CRM Pro yet.`,
    kpis: [
      { label: "Co-purchase Lift", value: "2.3×", trend: "up" },
      { label: "Strongest Pair", value: "Analytics → CRM Pro", trend: "neutral" },
      { label: "Target Accounts", value: "38", change: "+6", trend: "up" },
    ],
  };
}

export const COPILOT_SCENARIOS: CopilotScenario[] = [
  {
    id: "risk",
    title: "High-risk customers",
    description: "Find accounts showing churn signals and declining purchases.",
    icon: ShieldAlert,
    messages: [
      user("Which high-value customers are at risk?"),
      agent(getAgentResponse("Which customers are at risk?")),
      user("Which of them also reduced purchases after complaints?"),
      agent(getAgentResponse("reduced purchases after complaint")),
    ],
  },
  {
    id: "complaints",
    title: "Complaints & purchases",
    description: "See the main complaint reasons and how they affect buying.",
    icon: MessageSquareWarning,
    messages: [
      user("What are the main complaint reasons?"),
      agent(getAgentResponse("complaint reasons")),
      user("How much did purchases change after complaints?"),
      agent(getAgentResponse("reduced purchases after complaint")),
    ],
  },
  {
    id: "opportunity",
    title: "Growth opportunities",
    description: "Surface upsell and cross-sell opportunities across accounts.",
    icon: TrendingUp,
    messages: [
      user("Show me the best upsell opportunities"),
      agent(upsellResponse()),
      user("Which products are commonly cross-sold together?"),
      agent(crossSellResponse()),
    ],
  },
];
