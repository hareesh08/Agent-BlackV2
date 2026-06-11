import { createFileRoute, Link } from "@tanstack/react-router";
import { StatusBar } from "@/components/chat/StatusBar";
import { ArrowRight, Boxes, Zap, Clock, MessageSquare, Activity, TrendingUp, Bot } from "lucide-react";
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
    {
      label: "Total Queries",
      value: String(stats?.total_queries ?? "—"),
      icon: MessageSquare,
      gradient: "from-blue-500/10 to-blue-600/5",
      iconColor: "text-blue-400",
    },
    {
      label: "Active Agents",
      value: stats ? `${stats.active_agents} / ${stats.total_agents}` : "—",
      icon: Boxes,
      gradient: "from-emerald-500/10 to-emerald-600/5",
      iconColor: "text-emerald-400",
    },
    {
      label: "Uptime",
      value: uptime,
      icon: Clock,
      gradient: "from-purple-500/10 to-purple-600/5",
      iconColor: "text-purple-400",
    },
    {
      label: "Avg Response",
      value: stats?.avg_response_time != null ? `${stats.avg_response_time.toFixed(1)}s` : "—",
      icon: Zap,
      gradient: "from-amber-500/10 to-amber-600/5",
      iconColor: "text-amber-400",
    },
  ];

  return (
    <div className="mx-auto w-full max-w-[1100px] px-3 py-4 sm:px-4 sm:py-6 flex flex-col gap-6">
      <StatusBar />

      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Dashboard</h1>
          <p className="text-sm text-text-secondary mt-0.5">System overview and recent activity</p>
        </div>
        <Link
          to="/"
          search={{ new: "1" }}
          className="inline-flex items-center gap-1.5 rounded-xl bg-foreground px-4 py-2.5 text-sm text-background hover:opacity-90 transition-opacity shadow-sm"
        >
          New Query <ArrowRight className="h-3.5 w-3.5" />
        </Link>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {statCards.map(({ label, value, icon: Icon, gradient, iconColor }) => (
          <div
            key={label}
            className={`relative overflow-hidden rounded-xl border border-border bg-gradient-to-br ${gradient} p-4 sm:p-5 transition-all hover:shadow-md hover:border-border/80`}
          >
            <div className="absolute top-0 right-0 w-24 h-24 bg-gradient-to-br from-white/5 to-transparent rounded-full -translate-y-8 translate-x-8" />
            <div className="relative">
              <div className="flex items-center justify-between mb-3">
                <span className="text-[10px] uppercase tracking-wider text-text-muted font-medium">{label}</span>
                <div className={`p-1.5 rounded-lg bg-background/50 ${iconColor}`}>
                  <Icon className="h-4 w-4" />
                </div>
              </div>
              <div className="text-2xl font-bold tracking-tight sm:text-3xl">{value}</div>
            </div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2 rounded-xl border border-border bg-surface overflow-hidden">
          <div className="flex items-center justify-between border-b border-border px-4 py-3">
            <div className="flex items-center gap-2">
              <Activity className="h-4 w-4 text-text-muted" />
              <span className="text-sm font-semibold">Recent Activity</span>
            </div>
            <span className="text-xs text-text-muted">{recent.length} queries</span>
          </div>
          {recent.length === 0 ? (
            <div className="px-4 py-12 text-center">
              <MessageSquare className="mx-auto mb-3 h-8 w-8 text-text-muted/50" />
              <p className="text-sm text-text-muted">No queries yet</p>
              <p className="text-xs text-text-muted mt-1">Start a conversation on the Chat page</p>
            </div>
          ) : (
            <ul className="divide-y divide-border-light">
              {recent.slice(0, 6).map((r) => (
                <li key={r.id} className="flex items-center justify-between gap-3 px-4 py-3 hover:bg-surface-hover/50 transition-colors">
                  <div className="min-w-0 flex-1">
                    <div className="text-sm font-medium truncate">{r.query}</div>
                    <div className="text-[11px] text-text-muted mt-0.5">
                      {new Date(r.created_at * 1000).toLocaleString()}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {r.agents_used?.length ? (
                      <div className="flex items-center gap-1">
                        {r.agents_used.map((agent) => (
                          <span
                            key={agent}
                            className="inline-flex items-center gap-1 rounded-full bg-blue-500/10 border border-blue-500/20 px-2 py-0.5 text-[10px] font-medium text-blue-400"
                          >
                            <Bot className="h-2.5 w-2.5" />
                            {agent}
                          </span>
                        ))}
                      </div>
                    ) : (
                      <span className="text-[10px] text-text-muted">—</span>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="rounded-xl border border-border bg-surface p-5">
          <div className="flex items-center gap-2 mb-4">
            <TrendingUp className="h-4 w-4 text-text-muted" />
            <span className="text-sm font-semibold">Quick Stats</span>
          </div>
          <div className="space-y-4">
            <div className="flex items-center justify-between py-2 border-b border-border-light">
              <span className="text-xs text-text-secondary">Registered Tools</span>
              <span className="text-lg font-bold">39</span>
            </div>
            <div className="flex items-center justify-between py-2 border-b border-border-light">
              <span className="text-xs text-text-secondary">Agents</span>
              <span className="text-lg font-bold">3</span>
            </div>
            <div className="flex items-center justify-between py-2 border-b border-border-light">
              <span className="text-xs text-text-secondary">Tools per Agent</span>
              <span className="text-lg font-bold">13</span>
            </div>
            <div className="flex items-center justify-between py-2">
              <span className="text-xs text-text-secondary">Protocol</span>
              <span className="rounded-md border border-border bg-background px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider">
                A2A JSON-RPC
              </span>
            </div>
          </div>
          <div className="mt-4 pt-4 border-t border-border-light">
            <p className="text-[11px] text-text-muted text-center">
              Research · Solution · Experiment
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
