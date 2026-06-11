import { useState, useCallback, useMemo } from "react";
import {
  Copy, Check, ChevronRight, ChevronDown, Braces,
  Hash, Type, ToggleLeft, Parentheses,
} from "lucide-react";

type JsonValue = string | number | boolean | null | JsonValue[] | { [key: string]: JsonValue };

interface JsonNodeProps {
  keyName: string | null;
  value: JsonValue;
  depth: number;
  isLast: boolean;
  defaultExpanded?: boolean;
}

function getValueType(v: JsonValue): string {
  if (v === null) return "null";
  if (typeof v === "boolean") return "boolean";
  if (typeof v === "number") return "number";
  if (typeof v === "string") return "string";
  if (Array.isArray(v)) return "array";
  return "object";
}

function TypeIcon({ type }: { type: string }) {
  const cls = "h-3 w-3 shrink-0";
  switch (type) {
    case "string":
      return <Type className={`${cls} text-emerald-400`} />;
    case "number":
      return <Hash className={`${cls} text-amber-400`} />;
    case "boolean":
      return <ToggleLeft className={`${cls} text-blue-400`} />;
    case "null":
      return <Parentheses className={`${cls} text-text-muted`} />;
    case "array":
    case "object":
      return <Braces className={`${cls} text-purple-400`} />;
    default:
      return null;
  }
}

function JsonValueDisplay({ value }: { value: JsonValue }) {
  const type = getValueType(value);

  if (value === null) {
    return <span className="text-text-muted italic">null</span>;
  }

  if (typeof value === "boolean") {
    return (
      <span className={value ? "text-emerald-400" : "text-red-400"}>
        {String(value)}
      </span>
    );
  }

  if (typeof value === "number") {
    return <span className="text-amber-400">{value}</span>;
  }

  if (typeof value === "string") {
    const truncated = value.length > 120 ? value.slice(0, 120) + "..." : value;
    return (
      <span className="text-emerald-400 break-all">
        &quot;{truncated}&quot;
        {value.length > 120 && (
          <span className="text-text-muted ml-1">({value.length} chars)</span>
        )}
      </span>
    );
  }

  return null;
}

function JsonNode({ keyName, value, depth, isLast, defaultExpanded = false }: JsonNodeProps) {
  const type = getValueType(value);
  const isExpandable = type === "object" || type === "array";
  const [expanded, setExpanded] = useState(depth < 2 || defaultExpanded);

  const toggle = useCallback(() => {
    if (isExpandable) setExpanded((e) => !e);
  }, [isExpandable]);

  const childCount = useMemo(() => {
    if (type === "array") return (value as JsonValue[]).length;
    if (type === "object") return Object.keys(value as object).length;
    return 0;
  }, [type, value]);

  const childEntries = useMemo(() => {
    if (type === "array") {
      return (value as JsonValue[]).map((v, i) => ({ key: String(i), value: v }));
    }
    if (type === "object") {
      return Object.entries(value as Record<string, JsonValue>).map(([k, v]) => ({ key: k, value: v }));
    }
    return [];
  }, [type, value]);

  const indent = depth * 16;

  return (
    <div style={{ paddingLeft: indent }} className="group">
      <div
        className={`flex items-center gap-1.5 py-px rounded-sm transition-colors ${
          isExpandable ? "cursor-pointer hover:bg-surface-hover/50" : ""
        }`}
        onClick={toggle}
      >
        {isExpandable ? (
          <button className="shrink-0 p-0.5 rounded hover:bg-surface-hover">
            {expanded ? (
              <ChevronDown className="h-3 w-3 text-text-muted" />
            ) : (
              <ChevronRight className="h-3 w-3 text-text-muted" />
            )}
          </button>
        ) : (
          <span className="w-4 shrink-0" />
        )}

        <TypeIcon type={type} />

        {keyName !== null && (
          <span className="text-blue-300 text-xs font-medium">
            {keyName}
          </span>
        )}

        {keyName !== null && <span className="text-text-muted text-xs">:</span>}

        {isExpandable ? (
          <span className="text-text-muted text-xs">
            {expanded ? "{" : `[...]${!isLast ? "," : ""}`}
            {!expanded && type === "array" && (
              <span className="text-text-muted ml-1">({childCount} items)</span>
            )}
            {!expanded && type === "object" && (
              <span className="text-text-muted ml-1">({childCount} keys)</span>
            )}
          </span>
        ) : (
          <>
            <JsonValueDisplay value={value} />
            {!isLast && <span className="text-text-muted text-xs">,</span>}
          </>
        )}
      </div>

      {isExpandable && expanded && (
        <div className="border-l border-border/50 ml-2">
          {childEntries.map((entry, i) => (
            <JsonNode
              key={entry.key}
              keyName={type === "object" ? entry.key : null}
              value={entry.value}
              depth={depth + 1}
              isLast={i === childEntries.length - 1}
              defaultExpanded={depth < 1}
            />
          ))}
          <div style={{ paddingLeft: indent + 16 }} className="text-text-muted text-xs py-px">
            {type === "object" ? "}" : "]"}
            {!isLast && ","}
          </div>
        </div>
      )}
    </div>
  );
}

interface JsonViewerProps {
  data: unknown;
  className?: string;
}

export function JsonViewer({ data, className = "" }: JsonViewerProps) {
  const [copied, setCopied] = useState(false);

  const jsonString = useMemo(() => {
    try {
      return JSON.stringify(data, null, 2);
    } catch {
      return String(data);
    }
  }, [data]);

  const copy = async () => {
    await navigator.clipboard.writeText(jsonString);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  const keys = useMemo(() => {
    if (data && typeof data === "object" && !Array.isArray(data)) {
      return Object.keys(data).length;
    }
    if (Array.isArray(data)) {
      return data.length;
    }
    return 0;
  }, [data]);

  return (
    <div className={`rounded-xl border border-border bg-[#0d1117] overflow-hidden ${className}`}>
      <div className="flex items-center justify-between border-b border-border/50 bg-[#161b22] px-4 py-2">
        <div className="flex items-center gap-2">
          <Braces className="h-3.5 w-3.5 text-text-muted" />
          <span className="text-xs font-medium text-text-secondary">
            JSON {Array.isArray(data) ? `Array [${keys}]` : `Object {${keys}}`}
          </span>
        </div>
        <div className="flex items-center gap-1">
          <span className="text-[10px] text-text-muted font-mono mr-2">
            {(jsonString.length / 1024).toFixed(1)}KB
          </span>
          <button
            onClick={copy}
            className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-[11px] text-text-secondary hover:bg-surface-hover hover:text-foreground transition-colors"
          >
            {copied ? <Check className="h-3 w-3 text-emerald-400" /> : <Copy className="h-3 w-3" />}
            {copied ? "Copied" : "Copy"}
          </button>
        </div>
      </div>
      <div className="overflow-auto max-h-[500px] p-4">
        <pre className="font-mono text-[12px] leading-relaxed">
          {typeof data === "object" && data !== null ? (
            <JsonNode
              keyName={null}
              value={data as JsonValue}
              depth={0}
              isLast={true}
              defaultExpanded={true}
            />
          ) : (
            <JsonValueDisplay value={data as JsonValue} />
          )}
        </pre>
      </div>
    </div>
  );
}

interface JsonTreeViewProps {
  data: unknown;
  className?: string;
}

export function JsonTreeView({ data, className = "" }: JsonTreeViewProps) {
  const entries = useMemo(() => {
    if (!data || typeof data !== "object") return [];
    if (Array.isArray(data)) {
      return data.map((item, i) => ({ key: String(i), value: item }));
    }
    return Object.entries(data).map(([k, v]) => ({ key: k, value: v }));
  }, [data]);

  return (
    <div className={`space-y-1 ${className}`}>
      {entries.map(({ key, value }) => {
        const type = getValueType(value);
        return (
          <div key={key} className="rounded-lg border border-border bg-surface/30 p-3 hover:bg-surface/60 transition-colors">
            <div className="flex items-center gap-2">
              <TypeIcon type={type} />
              <span className="text-sm font-medium text-foreground">{key}</span>
              <span className="text-[10px] text-text-muted px-1.5 py-0.5 rounded bg-surface-hover">{type}</span>
            </div>
            {typeof value === "string" && (
              <p className="mt-1 text-xs text-text-secondary break-all">{value}</p>
            )}
            {typeof value === "number" && (
              <p className="mt-1 text-xs text-amber-400 font-mono">{value}</p>
            )}
            {typeof value === "boolean" && (
              <p className="mt-1 text-xs text-blue-400 font-mono">{String(value)}</p>
            )}
            {value === null && (
              <p className="mt-1 text-xs text-text-muted italic">null</p>
            )}
            {(type === "object" || type === "array") && (
              <div className="mt-2 ml-4 border-l-2 border-border pl-3">
                <JsonTreeView data={value} />
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
