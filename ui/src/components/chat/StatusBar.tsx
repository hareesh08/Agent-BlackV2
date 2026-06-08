import { useState, useMemo } from "react";
import { ChevronDown } from "lucide-react";
import { StatusDot } from "@/components/shared/StatusDot";
import { useAppStore } from "@/lib/store";
import { api, type AgentCard, type AgentStats, type SystemStatus } from "@/lib/api";
import { usePolling } from "@/hooks/use-polling";
import { useLiveUptime } from "@/hooks/use-live-uptime";

const AGENTS = [
  { name: "Research", port: 8001, key: "research-agent" },
  { name: "Solution", port: 8002, key: "solution-agent" },
  { name: "Experiment", port: 8003, key: "experiment-agent" },
];

export function StatusBar() {
  const [open, setOpen] = useState(true);
  const provider = useAppStore((s) => s.provider);

  const statusPoll = usePolling<SystemStatus>(() => api.status(), { interval: 15000 });
  const statsPoll = usePolling<AgentStats>(() => api.agentStats(), { interval: 15000 });
  const cardPoll = usePolling<{ agents: Record<string, AgentCard | { error: string }> }>(
    () => api.discoverAgents(),
    {
      interval: 30000,
    },
  );

  const status = statusPoll.data;
  const stats = statsPoll.data;
  const uptime = useLiveUptime(stats?.uptime ?? null);
  const cards = useMemo(
    () => Object.values(cardPoll.data?.agents || {}) as Array<AgentCard | { error: string }>,
    [cardPoll.data],
  );
  const cardCount = useMemo(
    () => cards.filter((card) => card?.supportedInterfaces?.length > 0).length,
    [cards],
  );

  return (
    <div className="rounded-xl border border-border bg-surface/60">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center justify-between gap-3 px-4 py-2.5"
      >
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
          {AGENTS.map((a) => (
            <span key={a.name} className="inline-flex items-center gap-1.5 text-xs">
              <StatusDot status={status?.agents?.[a.key] === "running" ? "online" : "offline"} />
              <span className="text-foreground font-medium">{a.name}</span>
              <span className="hidden text-text-muted sm:inline">:{a.port}</span>
            </span>
          ))}
        </div>
        <div className="flex items-center gap-2.5 text-xs text-text-secondary">
          <span className="hidden rounded-md border border-border bg-background px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider sm:inline">
            A2A JSON-RPC
          </span>
          <span className="hidden rounded-md border border-border bg-background px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider sm:inline">
            {cardCount}/3 cards
          </span>
          <span className="hidden sm:inline">
            Selection: <span className="text-foreground font-medium">auto</span>
          </span>
          <span className="rounded-md border border-border bg-background px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider">
            {provider}
          </span>
          <ChevronDown className={`h-3.5 w-3.5 transition-transform ${open ? "" : "-rotate-90"}`} />
        </div>
      </button>
      {open && (
        <div className="border-t border-border-light px-4 py-3 grid grid-cols-2 sm:grid-cols-5 gap-3 text-xs">
          <Stat label="Protocol" value="A2A" />
          <Stat label="Card Discovery" value={cardPoll.loading ? "checking" : `${cardCount}/3`} />
          <Stat
            label="Active Agents"
            value={stats ? `${stats.active_agents} / ${stats.total_agents}` : "—"}
          />
          <Stat label="Uptime" value={uptime} />
          <Stat
            label="Avg Response"
            value={
              stats?.avg_response_time != null ? `${stats.avg_response_time.toFixed(1)}s` : "—"
            }
          />
        </div>
      )}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col">
      <span className="text-text-muted text-[10px] uppercase tracking-wider">{label}</span>
      <span className="text-foreground font-medium">{value}</span>
    </div>
  );
}
