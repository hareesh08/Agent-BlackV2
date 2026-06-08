import { createFileRoute } from "@tanstack/react-router";
import { StatusDot } from "@/components/shared/StatusDot";
import { Collapsible } from "@/components/shared/Collapsible";
import { useEffect, useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";
import { Activity, BadgeCheck, Link2, RefreshCw } from "lucide-react";
import {
  api,
  type AgentCard,
  type AgentCardInterface,
  type AgentCardResponse,
  type AgentSkill,
  type DiscoAgent,
} from "@/lib/api";
import { usePolling } from "@/hooks/use-polling";

export const Route = createFileRoute("/agents")({
  head: () => ({ meta: [{ title: "Agents · Agent Black" }] }),
  component: AgentsPage,
});

const DEFAULT_TOOLS: Record<string, string[]> = {
  "research-agent": [
    "search_papers",
    "summarize_paper",
    "analyze_gaps",
    "find_cv_datasets",
    "recommend_cv_models",
    "citation_generator",
    "benchmark_search",
    "eval_metric_advisor",
    "architecture_comparison",
    "synthetic_data_strategy",
    "solution_recommendation",
    "prototype_guidance",
    "experiment_planner",
  ],
  "solution-agent": [
    "search_papers",
    "summarize_paper",
    "find_nlp_datasets",
    "rag_design",
    "llm_benchmark",
    "citation_generator",
    "prompt_optimizer",
    "information_extraction",
    "eval_metric_advisor",
    "analyze_gaps",
    "solution_recommendation",
    "prototype_guidance",
    "experiment_planner",
  ],
  "experiment-agent": [
    "search_papers",
    "plan_experiment",
    "eval_metric_advisor",
    "hyperparameter_advice",
    "recommend_models",
    "benchmark_search",
    "feature_engineering_advisor",
    "model_explainability_advisor",
    "time_series_strategy",
    "analyze_gaps",
    "solution_recommendation",
    "prototype_guidance",
    "summarize_paper",
  ],
};

const AGENT_KEYS: Record<string, string> = {
  "research-agent": "research",
  "solution-agent": "solution",
  "experiment-agent": "experiment",
  research: "research",
  solution: "solution",
  experiment: "experiment",
};

const AGENT_URLS: Record<string, string> = {
  research: "http://localhost:8001",
  solution: "http://localhost:8002",
  experiment: "http://localhost:8003",
};

function agentKey(name: string) {
  return AGENT_KEYS[name] || name.replace("-agent", "");
}

function interfaceFor(card: AgentCard | undefined): AgentCardInterface | undefined {
  return (
    card?.supportedInterfaces?.find((iface) => iface.protocolBinding === "JSONRPC") ||
    card?.supportedInterfaces?.[0]
  );
}

function cardUrl(agent: DiscoAgent, card: AgentCard | undefined) {
  const iface = interfaceFor(card);
  return (
    iface?.url || `${agent.url || AGENT_URLS[agentKey(agent.name)]}/.well-known/agent-card.json`
  );
}

function protocolLabel(card: AgentCard | undefined) {
  const iface = interfaceFor(card);
  if (!iface) return "A2A";
  return `${iface.protocolBinding}${iface.protocolVersion ? ` ${iface.protocolVersion}` : ""}`;
}

function skillLabel(skill: AgentSkill) {
  return skill.id || skill.name || "Skill";
}

function AgentsPage() {
  const [logs, setLogs] = useState<Record<string, { stdout: string; stderr: string }>>({});
  const [cards, setCards] = useState<Record<string, AgentCardResponse>>({});
  const latestCardsRef = useRef<Record<string, AgentCardResponse>>({});
  const [cardLoading, setCardLoading] = useState(false);

  const agentsPoll = usePolling<{ agents: DiscoAgent[] }>(() => api.getDiscoveredAgents(), {
    interval: 30000,
  });

  const agents = useMemo(
    () =>
      (agentsPoll.data?.agents ?? []).map((a) => ({
        ...a,
        tools: DEFAULT_TOOLS[a.name] || [],
      })),
    [agentsPoll.data],
  );

  const cardKeys = useMemo(() => agents.map((a) => `${a.name}:${a.url}`).join("|"), [agents]);

  useEffect(() => {
    let cancelled = false;

    const refreshCards = async () => {
      if (!agents.length) return;
      setCardLoading(true);
      try {
        const next: Record<string, AgentCardResponse> = { ...latestCardsRef.current };
        await Promise.all(
          agents.map(async (a) => {
            try {
              const response = await api.getAgentCard(agentKey(a.name));
              if (!cancelled) next[a.name] = response;
            } catch {
              if (!cancelled) delete next[a.name];
            }
          }),
        );
        if (!cancelled) {
          latestCardsRef.current = next;
          setCards(next);
          latestCardsRef.current = next;
        }
      } finally {
        if (!cancelled) setCardLoading(false);
      }
    };

    refreshCards();
    return () => {
      cancelled = true;
    };
  }, [cardKeys, agents]);

  const fetchLogs = async (name: string) => {
    try {
      const data = await api.getAgentLogs(name);
      setLogs((prev) => ({ ...prev, [name]: data }));
    } catch {
      return;
    }
  };

  const refreshCards = async () => {
    setCardLoading(true);
    try {
      const next: Record<string, AgentCardResponse> = {};
      await Promise.all(
        agents.map(async (a) => {
          try {
            next[a.name] = await api.getAgentCard(agentKey(a.name));
          } catch {
            return;
          }
        }),
      );
      setCards(next);
    } finally {
      setCardLoading(false);
    }
  };

  return (
    <div className="mx-auto w-full max-w-[1180px] px-3 py-4 sm:px-4 sm:py-6 flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Agents</h1>
          <p className="mt-1 text-xs text-text-secondary">
            Standard A2A cards, JSON-RPC endpoints, and legacy control surfaces.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={refreshCards}
            disabled={cardLoading || !agents.length}
            className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-surface px-3 py-1.5 text-xs hover:bg-surface-hover disabled:opacity-40"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${cardLoading ? "animate-spin" : ""}`} />
            Refresh cards
          </button>
          <button
            onClick={() => api.startAgents()}
            className="rounded-lg border border-border px-3 py-1.5 text-xs hover:bg-surface-hover"
          >
            Start All
          </button>
          <button
            onClick={() => api.stopAgents()}
            className="rounded-lg border border-border px-3 py-1.5 text-xs hover:bg-surface-hover"
          >
            Stop All
          </button>
        </div>
      </div>

      {agentsPoll.loading ? (
        <div className="flex items-center justify-center py-16 text-sm text-text-muted">
          Loading agents...
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {agents.map((a) => {
            const card = cards[a.name]?.card;
            const health = cards[a.name]?.health;
            const iface = interfaceFor(card);
            const skills = card?.skills || [];
            const inputModes = card?.defaultInputModes || [];
            const outputModes = card?.defaultOutputModes || [];
            const endpoint = cardUrl(a, card);
            const protocol = protocolLabel(card);

            return (
              <div
                key={a.name}
                className="rounded-xl border border-border bg-surface p-3 flex flex-col gap-3 sm:p-4"
              >
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <div className="flex items-center gap-2">
                      <StatusDot status={a.status === "running" ? "online" : "offline"} />
                      <h3 className="text-sm font-semibold">{a.name}</h3>
                    </div>
                    <p className="mt-0.5 text-xs text-text-muted font-mono">
                      :{a.port} ·{" "}
                      {a.last_seen ? new Date(a.last_seen * 1000).toLocaleTimeString() : "unknown"}
                    </p>
                  </div>
                  <span className="rounded-md border border-border bg-background px-2 py-1 text-[10px] font-mono uppercase tracking-wider">
                    {protocol}
                  </span>
                </div>

                <p className="text-xs text-text-secondary leading-relaxed">
                  {card?.description || "No A2A agent card discovered yet."}
                </p>

                <div className="grid grid-cols-2 gap-2">
                  <Metric
                    icon={<Activity className="h-3.5 w-3.5" />}
                    label="Health"
                    value={health || a.status}
                  />
                  <Metric
                    icon={<Link2 className="h-3.5 w-3.5" />}
                    label="A2A URL"
                    value={endpoint.replace(/^https?:\/\//, "")}
                  />
                </div>

                {(inputModes.length > 0 || outputModes.length > 0) && (
                  <div className="flex flex-wrap gap-1.5">
                    {inputModes.map((mode) => (
                      <span
                        key={`in-${mode}`}
                        className="rounded-full border border-border bg-background px-2 py-0.5 text-[10px] font-mono"
                      >
                        in: {mode}
                      </span>
                    ))}
                    {outputModes.map((mode) => (
                      <span
                        key={`out-${mode}`}
                        className="rounded-full border border-border bg-background px-2 py-0.5 text-[10px] font-mono"
                      >
                        out: {mode}
                      </span>
                    ))}
                  </div>
                )}

                {skills.length > 0 && (
                  <div>
                    <div className="text-[10px] uppercase tracking-wider text-text-muted mb-1.5 flex items-center gap-1.5">
                      <BadgeCheck className="h-3.5 w-3.5" />
                      A2A skills ({skills.length})
                    </div>
                    <div className="flex flex-wrap gap-1">
                      {skills.slice(0, 7).map((skill) => (
                        <span
                          key={skillLabel(skill)}
                          className="rounded-md border border-border bg-background px-2 py-0.5 text-[10px] font-mono"
                        >
                          {skillLabel(skill)}
                        </span>
                      ))}
                      {skills.length > 7 && (
                        <span className="rounded-md border border-border bg-background px-2 py-0.5 text-[10px] font-mono text-text-muted">
                          +{skills.length - 7}
                        </span>
                      )}
                    </div>
                  </div>
                )}

                <div>
                  <div className="text-[10px] uppercase tracking-wider text-text-muted mb-1.5">
                    {a.tools?.length || 0} tools
                  </div>
                  <div className="flex flex-wrap gap-1">
                    {a.tools?.slice(0, 6).map((t: string) => (
                      <span
                        key={t}
                        className="rounded-md border border-border bg-background px-2 py-0.5 text-[10px] font-mono"
                      >
                        {t}
                      </span>
                    ))}
                    {(a.tools?.length || 0) > 6 && (
                      <span className="rounded-md border border-border bg-background px-2 py-0.5 text-[10px] font-mono text-text-muted">
                        +{a.tools.length - 6}
                      </span>
                    )}
                  </div>
                </div>

                <Collapsible title="A2A Card" badge="card">
                  <pre className="text-[11px] font-mono text-text-secondary overflow-x-auto">
                    {JSON.stringify(card || { error: "Card unavailable" }, null, 2)}
                  </pre>
                </Collapsible>
                <Collapsible title="MCP Tools" badge="JSON">
                  <pre className="text-[11px] font-mono text-text-secondary overflow-x-auto">
                    {JSON.stringify({ tools: a.tools || [] }, null, 2)}
                  </pre>
                </Collapsible>
                <Collapsible title="Logs" badge="tail">
                  <div className="flex flex-col gap-2">
                    <button
                      onClick={() => fetchLogs(a.name)}
                      className="self-start rounded border border-border px-2 py-0.5 text-[10px] hover:bg-surface-hover"
                    >
                      Refresh logs
                    </button>
                    <pre className="text-[11px] font-mono text-text-secondary leading-relaxed max-h-40 overflow-y-auto">
                      {logs[a.name]?.stdout || `[INFO] Fetch logs to view output for ${a.name}`}
                    </pre>
                  </div>
                </Collapsible>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function Metric({ icon, label, value }: { icon: ReactNode; label: string; value: string }) {
  return (
    <div className="rounded-lg border border-border bg-background/50 p-2 min-w-0">
      <div className="flex items-center gap-1.5 text-[10px] uppercase tracking-wider text-text-muted">
        {icon}
        {label}
      </div>
      <div className="mt-1 truncate text-xs font-mono text-foreground">{value}</div>
    </div>
  );
}
