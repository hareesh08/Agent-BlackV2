import ReactMarkdown from "react-markdown";
import { BookOpen, Database, Cpu, FlaskConical, Lightbulb, AlertTriangle } from "lucide-react";
import { Collapsible } from "@/components/shared/Collapsible";
import type { ReportSections } from "@/lib/store";

const titles: Record<keyof ReportSections, string> = {
  literature_review: "Literature Review",
  datasets: "Datasets",
  models: "Models",
  evaluation_plan: "Evaluation Plan",
  prototype_guidance: "Prototype Guidance",
};

const sectionIcons: Record<keyof ReportSections, React.ReactNode> = {
  literature_review: <BookOpen className="h-3.5 w-3.5" />,
  datasets: <Database className="h-3.5 w-3.5" />,
  models: <Cpu className="h-3.5 w-3.5" />,
  evaluation_plan: <FlaskConical className="h-3.5 w-3.5" />,
  prototype_guidance: <Lightbulb className="h-3.5 w-3.5" />,
};

const titleKeys = [
  "title",
  "name",
  "component",
  "component_name",
  "label",
  "step",
  "step_name",
  "phase",
  "phase_name",
  "module",
  "module_name",
  "metric",
  "metric_name",
  "heading",
  "summary",
] as const;

function formatLabel(value: string) {
  return value.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function parseSection(raw: unknown): unknown {
  if (typeof raw === "object" && raw !== null) return raw;
  if (typeof raw === "string") {
    const trimmed = raw.trim();
    if (trimmed.startsWith("[") || trimmed.startsWith("{")) {
      try {
        const parsed = JSON.parse(trimmed);
        if (typeof parsed === "object" && parsed !== null) return parsed;
      } catch {}
    }
    return raw;
  }
  return raw;
}

function getCardTitle(paper: Record<string, unknown>): string {
  for (const key of titleKeys) {
    const value = paper[key];
    if (typeof value === "string" && value.trim()) return value;
  }

  for (const value of Object.values(paper)) {
    if (typeof value === "string" && value.trim()) return value;
  }

  return "Untitled";
}

function renderInlineValue(value: unknown): string {
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  return JSON.stringify(value);
}

function KeyValueList({ data }: { data: Record<string, unknown> }) {
  const entries = Object.entries(data);
  if (entries.length === 0) return null;

  return (
    <div className="mt-2 grid gap-2">
      {entries.map(([key, value]) => (
        <div key={key} className="rounded-md border border-border bg-background/40 p-2">
          <div className="text-[10px] font-medium uppercase tracking-wider text-text-muted">
            {formatLabel(key)}
          </div>
          {Array.isArray(value) ? (
            <div className="mt-1 flex flex-wrap gap-1.5">
              {value.map((item, index) => (
                <span
                  key={`${key}-${index}`}
                  className="rounded-full border border-border bg-surface px-2 py-0.5 text-[11px] text-text-secondary"
                >
                  {renderInlineValue(item)}
                </span>
              ))}
            </div>
          ) : isObject(value) ? (
            <div className="mt-1 grid gap-1">
              {Object.entries(value).map(([nestedKey, nestedValue]) => (
                <div key={nestedKey} className="text-xs text-text-secondary leading-relaxed">
                  <span className="font-medium text-foreground">{formatLabel(nestedKey)}:</span>{" "}
                  {renderInlineValue(nestedValue)}
                </div>
              ))}
            </div>
          ) : (
            <p className="mt-1 text-xs text-text-secondary leading-relaxed">{renderInlineValue(value)}</p>
          )}
        </div>
      ))}
    </div>
  );
}

function PaperCard({ paper, fallbackTitle }: { paper: Record<string, unknown>; fallbackTitle: string }) {
  const title = getCardTitle(paper) === "Untitled" ? fallbackTitle : getCardTitle(paper);
  const authors = Array.isArray(paper.authors)
    ? paper.authors.join(", ")
    : typeof paper.authors === "string" ? paper.authors : "";
  const year = paper.year ? String(paper.year) : "";
  const relevance = String(paper.relevance || paper.description || "");
  const purpose = String(paper.purpose || "");
  const split = paper.split as Record<string, number> | undefined;
  const details = Object.fromEntries(
    Object.entries(paper).filter(([key, value]) => {
      if (titleKeys.includes(key as (typeof titleKeys)[number])) return false;
      if (["authors", "year", "relevance", "description", "purpose", "split", "pros", "cons", "type"].includes(key)) return false;
      return value != null && value !== "";
    }),
  );

  return (
    <div className="rounded-lg border border-border bg-surface/50 p-3 flex flex-col gap-1.5 hover:bg-surface-hover/40 transition-colors">
      <h4 className="text-sm font-medium text-foreground leading-snug">{title}</h4>
      <div className="flex flex-wrap items-center gap-2 text-[11px] text-text-muted">
        {authors && <span>{authors}</span>}
        {year && (
          <span className="rounded-full bg-primary/10 px-2 py-0.5 text-primary font-medium">
            {year}
          </span>
        )}
        {paper.type && (
          <span className="rounded-full bg-blue-500/10 px-2 py-0.5 text-blue-400 font-medium">
            {String(paper.type)}
          </span>
        )}
      </div>
      {relevance && (
        <p className="text-xs text-text-secondary leading-relaxed mt-0.5">{relevance}</p>
      )}
      {purpose && (
        <p className="text-xs text-text-muted leading-relaxed italic">{purpose}</p>
      )}
      {split && typeof split === "object" && (
        <div className="flex gap-3 text-[10px] text-text-muted mt-0.5">
          {Object.entries(split).map(([k, v]) => (
            <span key={k}>
              <span className="font-medium text-text-secondary">{k}</span>: {String(v)}
            </span>
          ))}
        </div>
      )}
      {Object.keys(details).length > 0 && <KeyValueList data={details} />}
      {Array.isArray(paper.pros) && paper.pros.length > 0 && (
        <div className="mt-1">
          <span className="text-[10px] font-medium text-green-400 uppercase tracking-wider">Pros</span>
          <ul className="mt-0.5 space-y-0.5">
            {paper.pros.map((p: string, i: number) => (
              <li key={i} className="text-xs text-text-secondary flex items-start gap-1.5">
                <span className="text-green-400 mt-0.5">+</span> {p}
              </li>
            ))}
          </ul>
        </div>
      )}
      {Array.isArray(paper.cons) && paper.cons.length > 0 && (
        <div className="mt-1">
          <span className="text-[10px] font-medium text-red-400 uppercase tracking-wider">Cons</span>
          <ul className="mt-0.5 space-y-0.5">
            {paper.cons.map((c: string, i: number) => (
              <li key={i} className="text-xs text-text-secondary flex items-start gap-1.5">
                <span className="text-red-400 mt-0.5">-</span> {c}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function ArraySection({ label, items }: { label: string; items: unknown[] }) {
  if (items.length === 0) return null;
  const allObjects = items.every((item) => typeof item === "object" && item !== null);

  return (
    <div>
      <h4 className="text-[11px] uppercase tracking-wider text-text-muted font-medium mb-2">
        {label.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
        <span className="ml-1.5 text-text-secondary">({items.length})</span>
      </h4>
      <div className="flex flex-col gap-2">
        {allObjects
          ? items.map((item, i) => (
              <PaperCard
                key={i}
                paper={item as Record<string, unknown>}
                fallbackTitle={`${formatLabel(label)} ${i + 1}`}
              />
            ))
          : items.map((item, i) => (
               <div key={i} className="text-xs text-text-secondary bg-surface/50 rounded-md px-3 py-1.5">
                 {typeof item === "string" ? item : JSON.stringify(item)}
              </div>
            ))
        }
      </div>
    </div>
  );
}

function TextSection({ label, value }: { label: string; value: string }) {
  const words = value.split(/\s+/).length;
  const isLong = words > 40;

  return (
    <Collapsible title={label.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())} defaultOpen={!isLong}>
      <div className="text-xs text-text-secondary leading-relaxed">
        <ReactMarkdown>{value}</ReactMarkdown>
      </div>
    </Collapsible>
  );
}

function ObjectSection({ label, value }: { label: string; value: Record<string, unknown> }) {
  return (
    <Collapsible title={formatLabel(label)} defaultOpen>
      <KeyValueList data={value} />
    </Collapsible>
  );
}

function ParsedSectionContent({ data }: { data: unknown }) {
  if (Array.isArray(data)) {
    return <ArraySection label="Items" items={data} />;
  }

  if (data && typeof data === "object") {
    const obj = data as Record<string, unknown>;

    if (Array.isArray(obj.papers) && obj.papers.length > 0) {
      const keyConcepts = obj.key_concepts as Record<string, unknown> | undefined;

      return (
        <div className="flex flex-col gap-3">
          <ArraySection label="Papers" items={obj.papers} />

          {keyConcepts && typeof keyConcepts === "object" && (
            <div>
              <h4 className="text-[11px] uppercase tracking-wider text-text-muted font-medium mb-2">
                Key Concepts
              </h4>
              <div className="flex flex-col gap-2">
                {Object.entries(keyConcepts).map(([k, v]) => (
                  isObject(v) ? (
                    <ObjectSection key={k} label={k} value={v} />
                  ) : (
                    <Collapsible key={k} title={formatLabel(k)} defaultOpen>
                      <div className="text-xs text-text-secondary leading-relaxed">
                        <ReactMarkdown>{typeof v === "string" ? v : JSON.stringify(v, null, 2)}</ReactMarkdown>
                      </div>
                    </Collapsible>
                  )
                ))}
              </div>
            </div>
          )}
        </div>
      );
    }

    const entries = Object.entries(obj);
    if (entries.length > 0) {
      return (
        <div className="flex flex-col gap-2">
          {entries.map(([k, v]) => (
            <div key={k}>
              {Array.isArray(v) ? (
                <ArraySection label={k} items={v} />
              ) : isObject(v) ? (
                <ObjectSection label={k} value={v} />
              ) : (
                <div className="rounded-lg border border-border bg-surface/30 p-2.5">
                  <span className="text-[11px] font-medium text-text-muted uppercase tracking-wider">
                    {k.replace(/_/g, " ")}
                  </span>
                  <p className="text-xs text-text-secondary mt-1 leading-relaxed">{String(v)}</p>
                </div>
              )}
            </div>
          ))}
        </div>
      );
    }
  }

  const text = typeof data === "string" ? data : JSON.stringify(data, null, 2);
  return (
    <div className="md-body">
      <ReactMarkdown>{text}</ReactMarkdown>
    </div>
  );
}

function ErrorReport({ report }: { report: Record<string, unknown> }) {
  const message = String(report.message || "Unknown error");
  const reason = typeof report.reason === "string" ? report.reason : "";
  const suggestion = typeof report.suggestion === "string" ? report.suggestion : "";
  const topics = Array.isArray(report.supported_topics) ? report.supported_topics : [];
  const validation = report.validation && typeof report.validation === "object"
    ? report.validation as Record<string, unknown>
    : null;

  return (
    <div className="rounded-lg border border-amber-500/30 bg-amber-500/5 p-4">
      <div className="flex items-center gap-2 mb-2">
        <AlertTriangle className="h-4 w-4 text-amber-400" />
        <span className="text-sm font-medium text-amber-300">Not a research query</span>
      </div>
      <p className="text-sm text-text-secondary leading-relaxed mb-3">{message}</p>
      {reason && <p className="mb-3 text-xs leading-relaxed text-text-muted">{reason}</p>}
      {suggestion && (
        <div className="mb-3 rounded-md border border-border bg-background/50 px-3 py-2 text-xs text-text-secondary">
          <span className="font-medium text-foreground">Suggestion:</span> {suggestion}
        </div>
      )}
      {topics.length > 0 && (
        <div>
          <p className="text-[11px] uppercase tracking-wider text-text-muted font-medium mb-1.5">
            Supported topics
          </p>
          <ul className="flex flex-wrap gap-1.5">
            {topics.map((topic, i) => (
              <span
                key={i}
                className="rounded-full border border-border bg-background px-2 py-0.5 text-[11px] text-text-secondary"
              >
                {String(topic)}
              </span>
            ))}
          </ul>
        </div>
      )}
      {validation && (
        <div className="mt-3">
          <p className="text-[11px] uppercase tracking-wider text-text-muted font-medium mb-1.5">
            Validation details
          </p>
          <div className="rounded-md border border-border bg-background/50 p-3 text-xs text-text-secondary">
            <KeyValueList data={validation} />
          </div>
        </div>
      )}
    </div>
  );
}

export function ReportSections({ sections }: { sections: ReportSections }) {
  const raw = sections as Record<string, unknown>;

  if (raw?.error === "not_research_query") {
    return <ErrorReport report={raw} />;
  }

  const keys = Object.keys(titles) as (keyof ReportSections)[];
  return (
    <div className="flex flex-col gap-2">
      {keys.map((k, i) => {
        const value = sections[k];
        const data = parseSection(value);
        return (
          <Collapsible key={k} title={titles[k]} defaultOpen={i === 0} badge={sectionIcons[k]}>
            {data != null && data !== "" ? (
              <ParsedSectionContent data={data} />
            ) : (
              <p className="text-sm text-text-muted italic">
                Not applicable for this query
              </p>
            )}
          </Collapsible>
        );
      })}
    </div>
  );
}
