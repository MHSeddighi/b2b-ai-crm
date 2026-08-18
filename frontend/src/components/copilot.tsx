import { useEffect, useRef, useState } from "react";
import { Maximize2, Minimize2, Send, Sparkles, X } from "lucide-react";
import {
  Bar,
  BarChart,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { CustomerTable } from "@/components/customer-table";
import { getAgentResponse, delayResponse, type AgentResponse } from "@/lib/agent";
import { suggestedQuestions } from "@/lib/mock-data";
import { COPILOT_SCENARIOS, type CopilotScenario } from "@/lib/copilot-scenarios";
import { formatCompact } from "@/lib/utils";
import type { Kpi } from "@/lib/types";

export type Message =
  | { id: string; role: "user"; content: string }
  | { id: string; role: "agent"; response: AgentResponse };

const chartColors = ["#6366f1", "#8b5cf6", "#10b981", "#f59e0b", "#ef4444", "#06b6d4"];

function AgentAvatar() {
  return (
    <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-indigo-500 to-violet-500 text-white">
      <Sparkles className="h-3.5 w-3.5" />
    </div>
  );
}

function KpiGrid({ kpis }: { kpis: Kpi[] }) {
  return (
    <div className="mt-3 grid grid-cols-2 gap-2">
      {kpis.map((kpi) => (
        <div
          key={kpi.label}
          className="rounded-lg border bg-card p-2.5"
        >
          <p className="truncate text-[11px] text-muted-foreground">{kpi.label}</p>
          <p className="mt-0.5 truncate text-sm font-semibold tabular-nums">{kpi.value}</p>
        </div>
      ))}
    </div>
  );
}

function AgentChart({ response }: { response: AgentResponse }) {
  if (!response.chart) return null;
  const { chart } = response;

  return (
    <div className="mt-3 rounded-lg border bg-card p-3">
      <p className="mb-2 text-xs font-medium text-muted-foreground">{chart.title}</p>
      <div className="h-40">
        {chart.kind === "bar" ? (
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chart.data} margin={{ top: 4, right: 4, left: -24, bottom: 0 }}>
              <XAxis
                dataKey="name"
                tickLine={false}
                axisLine={false}
                tick={{ fontSize: 10 }}
                interval={0}
                className="text-muted-foreground"
              />
              <YAxis
                tickLine={false}
                axisLine={false}
                tick={{ fontSize: 10 }}
                className="text-muted-foreground"
              />
              <Tooltip
                cursor={{ fill: "hsl(var(--muted))" }}
                contentStyle={{ borderRadius: 8, border: "1px solid hsl(var(--border))", fontSize: 12 }}
              />
              <Bar dataKey="value" radius={[3, 3, 0, 0]} barSize={22}>
                {chart.data.map((_, i) => (
                  <Cell key={i} fill={chartColors[i % chartColors.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <div className="flex h-full items-center">
            <div className="h-36 w-36 shrink-0">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={chart.data}
                    dataKey="value"
                    nameKey="name"
                    innerRadius={32}
                    outerRadius={58}
                    paddingAngle={2}
                  >
                    {chart.data.map((_, i) => (
                      <Cell key={i} fill={chartColors[i % chartColors.length]} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{ borderRadius: 8, border: "1px solid hsl(var(--border))", fontSize: 12 }}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <ul className="flex-1 space-y-1.5 pl-2">
              {chart.data.map((d) => (
                <li key={d.name} className="flex items-center justify-between text-xs">
                  <span className="flex items-center gap-1.5 text-muted-foreground">
                    <span className="h-2 w-2 rounded-full" style={{ background: chartColors[chart.data.indexOf(d) % chartColors.length] }} />
                    {d.name}
                  </span>
                  <span className="font-medium tabular-nums">{formatCompact(d.value)}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}

function AgentMessage({ message }: { message: Extract<Message, { role: "agent" }> }) {
  const { response } = message;
  return (
    <div className="flex gap-2.5">
      <AgentAvatar />
      <div className="min-w-0 flex-1 space-y-1">
        <div className="rounded-2xl rounded-tl-sm bg-muted px-3.5 py-2.5 text-sm leading-relaxed text-foreground">
          {response.text}
        </div>
        {response.kpis && <KpiGrid kpis={response.kpis} />}
        {response.chart && <AgentChart response={response} />}
        {response.customers && (
          <div className="overflow-hidden rounded-lg border bg-card">
            <div className="px-3 py-1.5 text-xs font-medium text-muted-foreground">
              Affected customers
            </div>
            <CustomerTable data={response.customers} pageSize={4} dense toolbar={false} />
          </div>
        )}
      </div>
    </div>
  );
}

function UserMessage({ message }: { message: Extract<Message, { role: "user" }> }) {
  return (
    <div className="flex justify-end">
      <div className="max-w-[85%] rounded-2xl rounded-tr-sm bg-primary px-3.5 py-2.5 text-sm text-primary-foreground">
        {message.content}
      </div>
    </div>
  );
}

function TypingIndicator() {
  return (
    <div className="flex gap-2.5">
      <AgentAvatar />
      <div className="min-w-0 flex-1 space-y-2">
        <div className="rounded-2xl rounded-tl-sm bg-muted p-3">
          <div className="flex items-center gap-1.5">
            <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted-foreground/60 [animation-delay:0ms]" />
            <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted-foreground/60 [animation-delay:120ms]" />
            <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted-foreground/60 [animation-delay:240ms]" />
          </div>
        </div>
        <Skeleton className="h-16 w-full" />
      </div>
    </div>
  );
}

export type CopilotMode = "float" | "dock";

interface CopilotProps {
  onClose: () => void;
  mode?: CopilotMode;
  onToggleMode?: () => void;
}

export function Copilot({ onClose, mode = "float", onToggleMode }: CopilotProps) {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome",
      role: "agent",
      response: {
        text: "Hi, I'm your Customer Intelligence Copilot. Ask me anything about your customers, risk, or complaints.",
      },
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const idRef = useRef(1);

  useEffect(() => {
    const el = scrollRef.current;
    if (el) {
      el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
    }
  }, [messages, loading]);

  async function send(text?: string) {
    const question = (text ?? input).trim();
    if (!question || loading) return;

    setInput("");
    setMessages((prev) => [
      ...prev,
      { id: `u${idRef.current++}`, role: "user", content: question },
    ]);
    setLoading(true);

    const response = getAgentResponse(question);
    await delayResponse();

    setMessages((prev) => [
      ...prev,
      { id: `a${idRef.current++}`, role: "agent", response },
    ]);
    setLoading(false);
    inputRef.current?.focus();
  }

  function loadScenario(scenario: CopilotScenario) {
    setMessages(scenario.messages);
  }

  return (
    <div className="flex h-full flex-col bg-card">
      <div className="flex h-14 shrink-0 items-center gap-2 border-b px-4">
        <AgentAvatar />
        <div className="flex min-w-0 flex-col leading-tight">
          <span className="text-sm font-semibold">Copilot</span>
          <span className="inline-flex items-center gap-1 text-[11px] text-emerald-500">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
            Online · mock data
          </span>
        </div>
        <div className="ml-auto flex items-center gap-1">
          {onToggleMode && (
            <Button
              variant="ghost"
              size="icon"
              onClick={onToggleMode}
              aria-label={mode === "dock" ? "Float copilot" : "Expand copilot"}
              title={mode === "dock" ? "Float copilot" : "Expand copilot"}
            >
              {mode === "dock" ? (
                <Minimize2 className="h-4 w-4" />
              ) : (
                <Maximize2 className="h-4 w-4" />
              )}
            </Button>
          )}
          <Button
            variant="ghost"
            size="icon"
            onClick={onClose}
            aria-label="Close copilot"
          >
            <X className="h-4 w-4" />
          </Button>
        </div>
      </div>

      <div
        ref={scrollRef}
        className="scrollbar-thin min-h-0 flex-1 overflow-y-auto px-4 py-4"
      >
        <div className="flex flex-col gap-4">
          {messages.map((message) =>
            message.role === "user" ? (
              <UserMessage key={message.id} message={message} />
            ) : (
              <AgentMessage key={message.id} message={message} />
            )
          )}
          {!loading && messages.length <= 1 && (
            <div className="space-y-2">
              <p className="px-0.5 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Try a scenario
              </p>
              <div className="grid gap-2">
                {COPILOT_SCENARIOS.map((s) => {
                  const Icon = s.icon;
                  return (
                    <button
                      key={s.id}
                      onClick={() => loadScenario(s)}
                      className="flex items-start gap-3 rounded-xl border bg-card p-3 text-left transition-colors hover:border-primary/40 hover:bg-accent"
                    >
                      <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                        <Icon className="h-4 w-4" />
                      </span>
                      <span className="min-w-0">
                        <span className="block text-sm font-medium">{s.title}</span>
                        <span className="block text-xs text-muted-foreground">
                          {s.description}
                        </span>
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>
          )}
          {loading && <TypingIndicator />}
        </div>
      </div>

      <div className="shrink-0 space-y-2 border-t p-3">
        {!loading && messages.length <= 1 && (
          <div className="flex flex-wrap gap-2">
            {suggestedQuestions.map((q) => (
              <button
                key={q}
                onClick={() => send(q)}
                className="rounded-full border bg-background px-3 py-1 text-xs text-muted-foreground transition-colors hover:border-primary/50 hover:text-foreground"
              >
                {q}
              </button>
            ))}
          </div>
        )}

        <form
          className="flex items-center gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            send();
          }}
        >
          <Input
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about customers, risk, complaints..."
            className="flex-1"
            aria-label="Message the copilot"
            disabled={loading}
          />
          <Button
            type="submit"
            size="icon"
            disabled={loading || !input.trim()}
            aria-label="Send message"
          >
            <Send className="h-4 w-4" />
          </Button>
        </form>
      </div>
    </div>
  );
}
