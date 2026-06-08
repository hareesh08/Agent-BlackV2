import { type TaskEvent } from "@/lib/store";
import { Check, Loader2, X, ChevronRight, Circle, Network } from "lucide-react";

const stepMeta: Record<string, { label: string; group: "orchestrator" | "agents" | "output" }> = {
  submitted: { label: "Query submitted", group: "orchestrator" },
  validating_query: { label: "Validating query", group: "orchestrator" },
  selecting_agents: { label: "Selecting agents", group: "orchestrator" },
  decomposing_task: { label: "Decomposing task", group: "orchestrator" },
  aggregating: { label: "Aggregating results", group: "output" },
  research_task: { label: "Research Agent", group: "agents" },
  solution_task: { label: "Solution Agent", group: "agents" },
  experiment_task: { label: "Experiment Agent", group: "agents" },
  research: { label: "Research Agent", group: "agents" },
  solution: { label: "Solution Agent", group: "agents" },
  experiment: { label: "Experiment Agent", group: "agents" },
};

function StatusIcon({ status }: { status: string }) {
  if (status === "running") {
    return <Loader2 className="h-3 w-3 animate-spin text-blue-400" />;
  }
  if (status === "complete") {
    return <Check className="h-3 w-3 text-green-400" />;
  }
  if (status === "error") {
    return <X className="h-3 w-3 text-red-400" />;
  }
  return <Circle className="h-2 w-2 text-text-muted" />;
}

function deduplicateEvents(events: TaskEvent[]): TaskEvent[] {
  const latest = new Map<string, TaskEvent>();
  for (const ev of events) {
    const existing = latest.get(ev.step);
    if (!existing || ev.timestamp >= existing.timestamp) {
      latest.set(ev.step, ev);
    }
  }
  return Array.from(latest.values());
}

function orderSteps(steps: string[]): string[] {
  const order = [
    "submitted",
    "validating_query",
    "selecting_agents",
    "decomposing_task",
    "aggregating",
  ];
  return steps.sort((a, b) => {
    const ai = order.indexOf(a);
    const bi = order.indexOf(b);
    return (ai === -1 ? 99 : ai) - (bi === -1 ? 99 : bi);
  });
}

export function TaskProgress({ events }: { events: TaskEvent[] }) {
  if (!events || events.length === 0) return null;

  const unique = deduplicateEvents(events);

  const orchestratorSteps = orderSteps(
    unique
      .filter((ev) => {
        const meta = stepMeta[ev.step];
        return meta?.group === "orchestrator" || ev.step === "submitted";
      })
      .map((ev) => ev.step),
  );
  const orchestratorEvents = orchestratorSteps.map(
    (step) => unique.find((ev) => ev.step === step)!,
  );

  const agentSteps = unique
    .filter((ev) => stepMeta[ev.step]?.group === "agents")
    .map((ev) => ev.step);
  const agentEvents = agentSteps.map((step) => unique.find((ev) => ev.step === step)!);

  const outputSteps = unique
    .filter((ev) => stepMeta[ev.step]?.group === "output")
    .map((ev) => ev.step);
  const outputEvents = outputSteps.map((step) => unique.find((ev) => ev.step === step)!);

  const hasAgents = agentEvents.length > 0;
  const activeAgentCount = agentEvents.filter((e) => e.status === "running").length;
  const doneAgentCount = agentEvents.filter((e) => e.status === "complete").length;

  return (
    <div className="mb-3 rounded-xl border border-border bg-surface/50 p-3 text-xs">
      <div className="mb-2 flex items-center gap-2 text-[11px] font-medium text-text-muted uppercase tracking-wider">
        <Network className="h-3 w-3" />
        A2A Agent Pipeline
      </div>

      <div className="relative">
        <div className="absolute left-[7px] top-0 bottom-0 w-px bg-border" />

        <div className="space-y-0.5">
          {orchestratorEvents.map((ev) => {
            const meta = stepMeta[ev.step];
            return (
              <div key={ev.step} className="relative flex items-center gap-2 pl-0">
                <div className="relative z-10 flex h-4 w-4 items-center justify-center rounded-full bg-surface">
                  <StatusIcon status={ev.status} />
                </div>
                <span
                  className={`text-xs ${ev.status === "running" ? "text-foreground" : ev.status === "complete" ? "text-text-secondary" : "text-text-muted"}`}
                >
                  {meta?.label || ev.step}
                </span>
                {ev.status === "running" && (
                  <span className="text-[10px] text-text-muted ml-1 animate-pulse">...</span>
                )}
              </div>
            );
          })}
        </div>

        {hasAgents && (
          <div className="relative mt-1 ml-0">
            <div className="absolute left-[7px] top-0 h-2 w-px bg-border" />

            <div className="ml-5 rounded-lg border border-border/50 bg-background/50 p-2 mt-1">
              <div className="flex items-center gap-1.5 mb-1.5 text-[10px] text-text-muted font-medium uppercase tracking-wider">
                <ChevronRight className="h-2.5 w-2.5" />
                Invoking sub-agents over A2A
                {activeAgentCount > 0 && (
                  <span className="ml-1 rounded-full bg-blue-500/10 px-1.5 py-0 text-blue-400">
                    {activeAgentCount} active
                  </span>
                )}
                {doneAgentCount > 0 && (
                  <span className="ml-1 rounded-full bg-green-500/10 px-1.5 py-0 text-green-400">
                    {doneAgentCount} done
                  </span>
                )}
              </div>
              <div className="space-y-0.5">
                {agentEvents.map((ev) => {
                  const meta = stepMeta[ev.step];
                  return (
                    <div key={ev.step} className="flex items-center gap-2">
                      <div className="relative z-10 flex h-3.5 w-3.5 items-center justify-center rounded-full bg-surface">
                        <StatusIcon status={ev.status} />
                      </div>
                      <span
                        className={`text-xs ${ev.status === "running" ? "text-foreground" : ev.status === "complete" ? "text-text-secondary" : "text-text-muted"}`}
                      >
                        {meta?.label || ev.step}
                      </span>
                      {ev.status === "running" && (
                        <Loader2 className="h-2.5 w-2.5 animate-spin text-blue-400" />
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        )}

        {outputEvents.length > 0 && (
          <div className="space-y-0.5 mt-1">
            {outputEvents.map((ev) => {
              const meta = stepMeta[ev.step];
              return (
                <div key={ev.step} className="relative flex items-center gap-2 pl-0">
                  <div className="relative z-10 flex h-4 w-4 items-center justify-center rounded-full bg-surface">
                    <StatusIcon status={ev.status} />
                  </div>
                  <span
                    className={`text-xs ${ev.status === "running" ? "text-foreground" : ev.status === "complete" ? "text-text-secondary" : "text-text-muted"}`}
                  >
                    {meta?.label || ev.step}
                  </span>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
