import { createFileRoute, Link } from "@tanstack/react-router";
import { StatusBar } from "@/components/chat/StatusBar";
import { ArrowRight, Boxes, Zap, Clock, MessageSquare } from "lucide-react";
import { api, type AgentStats, type HistoryItem } from "@/lib/api";
import { usePolling } from "@/hooks/use-polling";
import { useLiveUptime } from "@/hooks/use-live-uptime";

export const Route = createFileRoute("/dashboard")({
  head: () => ({ meta: [{ title: "Dashboard · Agent Black" }] }),
  component: Dashboard,
});

function Dashboard() {
  const statsPoll = usePolling<AgentStats>(() => api.agentStats(), { interval: 30000 });
  const historyPoll = usePolling<HistoryItem[]>(() => api.queryHistory(), { interval: 30000 });

  const stats = statsPoll.data;
  const recent = historyPoll.data ?? [];
  const uptime = useLiveUptime(stats?.uptime ?? null);

  const statCards = [
    { label: "Total Queries", value: String(stats?.total_queries ?? "—"), icon: MessageSquare },
    { label: "Active Agents", value: stats ? `${stats.active_agents} / ${stats.total_agents}` : "—", icon: Boxes },
    { label: "Uptime", value: uptime, icon: Clock },
    { label: "Avg Response", value: stats?.avg_response_time != null ? `${stats.avg_response_time.toFixed(1)}s` : "—", icon: Zap },
  ];

  return (
    <div className="mx-auto w-full max-w-[1100px] px-3 py-4 sm:px-4 sm:py-6 flex flex-col gap-6">
      <StatusBar />

      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold tracking-tight">Dashboard</h1>
        <Link
          to="/"
          className="inline-flex items-center gap-1.5 rounded-lg bg-foreground px-3 py-2 text-sm text-background hover:opacity-90"
        >
          New Query <ArrowRight className="h-3.5 w-3.5" />
        </Link>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {statCards.map(({ label, value, icon: Icon }) => (
          <div key={label} className="rounded-xl border border-border bg-surface p-3 sm:p-4">
            <div className="flex items-center justify-between">
              <span className="text-[10px] uppercase tracking-wider text-text-muted">{label}</span>
              <Icon className="h-4 w-4 text-text-muted" />
            </div>
            <div className="mt-2 text-xl font-semibold tracking-tight sm:text-2xl">{value}</div>
          </div>
        ))}
      </div>

      <div className="rounded-xl border border-border bg-surface">
        <div className="border-b border-border-light px-4 py-3 text-sm font-semibold">
          Recent Activity
        </div>
        {recent.length === 0 ? (
          <div className="px-4 py-6 text-center text-sm text-text-muted">
            No queries yet. Start a conversation on the Chat page.
          </div>
        ) : (
          <ul className="divide-y divide-border-light">
            {recent.map((r) => (
              <li key={r.id} className="flex items-center justify-between gap-3 px-3 py-3 sm:px-4">
                <div className="min-w-0 flex-1 truncate text-sm">{r.query}</div>
                <span className="hidden rounded-full border border-border bg-background px-2 py-0.5 text-[10px] text-text-secondary sm:inline">
                  {r.agents_used?.join(" + ") || "—"}
                </span>
                <span className="text-xs text-text-muted whitespace-nowrap">
                  {new Date(r.created_at * 1000).toLocaleString()}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="rounded-xl border border-border bg-surface p-4">
        <div className="text-sm font-semibold">Tools Registered</div>
        <div className="mt-2 text-3xl font-semibold tracking-tight">39</div>
        <p className="mt-1 text-xs text-text-secondary">13 tools per agent · across Research, Solution, Experiment</p>
      </div>
    </div>
  );
}
