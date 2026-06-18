import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { useAppStore } from "@/lib/store";
import { useDarkMode } from "@/hooks/use-dark-mode";
import { api, type SettingsResponse, type AgentNetworkConfig } from "@/lib/api";

export const Route = createFileRoute("/settings")({
  head: () => ({ meta: [{ title: "Settings · Agent Black" }] }),
  component: SettingsPage,
});

const AGENT_KEYS = ["research", "solution", "experiment"] as const;
const AGENT_DEFAULTS: Record<string, { host: string; port: number }> = {
  research: { host: "", port: 8001 },
  solution: { host: "", port: 8002 },
  experiment: { host: "", port: 8003 },
};

function SettingsPage() {
  const provider = useAppStore((s) => s.provider);
  const setProvider = useAppStore((s) => s.setProvider);
  const { darkMode, setDarkMode } = useDarkMode();

  const [settings, setSettings] = useState<SettingsResponse | null>(null);
  const [apiKey, setApiKey] = useState("");
  const [model, setModel] = useState("");
  const [baseUrl, setBaseUrl] = useState("");
  const [kaggleUsername, setKaggleUsername] = useState("");
  const [kaggleKey, setKaggleKey] = useState("");
  const [agentNetwork, setAgentNetwork] = useState<
    Record<string, AgentNetworkConfig>
  >({
    research: { network_mode: false, network_host: "", network_port: 8001 },
    solution: { network_mode: false, network_host: "", network_port: 8002 },
    experiment: { network_mode: false, network_host: "", network_port: 8003 },
  });
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState("");

  useEffect(() => {
    api
      .getSettings()
      .then((s) => {
        setSettings(s);
        setProvider(s.llm_provider as "gemini" | "openai" | "anthropic");
        const cur = s.providers[s.llm_provider];
        setModel(cur?.model || "");
        setBaseUrl(cur?.base_url || "");
        setKaggleUsername(s.kaggle_username || "");
        if (s.agent_network) {
          setAgentNetwork((prev) => {
            const next = { ...prev };
            for (const key of AGENT_KEYS) {
              const cfg = s.agent_network[key];
              if (cfg) {
                next[key] = cfg;
              }
            }
            return next;
          });
        }
      })
      .catch(() => {});
  }, []);

  const handleSave = async () => {
    setSaving(true);
    setMsg("");
    try {
      const payload: Record<string, any> = { llm_provider: provider };
      if (apiKey) payload[`${provider}_api_key`] = apiKey;
      if (baseUrl) payload[`${provider}_base_url`] = baseUrl;
      if (model) payload[`${provider}_model`] = model;
      payload.kaggle_username = kaggleUsername || undefined;
      if (kaggleKey) payload.kaggle_key = kaggleKey;
      payload.agent_network = {};
      for (const key of AGENT_KEYS) {
        const cfg = agentNetwork[key];
        payload.agent_network[key] = {
          network_mode: cfg.network_mode,
          network_host: cfg.network_host,
          network_port: cfg.network_port,
        };
      }
      await api.updateSettings(payload);
      setMsg("Settings saved successfully");
      setApiKey("");
    } catch (err: any) {
      setMsg(`Error: ${err.message}`);
    } finally {
      setSaving(false);
    }
  };

  const toggleNetwork = (key: string) => {
    setAgentNetwork((prev) => ({
      ...prev,
      [key]: {
        ...prev[key],
        network_mode: !prev[key].network_mode,
      },
    }));
  };

  const updateNetworkHost = (key: string, host: string) => {
    setAgentNetwork((prev) => ({
      ...prev,
      [key]: { ...prev[key], network_host: host },
    }));
  };

  const updateNetworkPort = (key: string, port: string) => {
    const num = parseInt(port, 10);
    setAgentNetwork((prev) => ({
      ...prev,
      [key]: { ...prev[key], network_port: isNaN(num) ? 0 : num },
    }));
  };

  return (
    <div className="mx-auto w-full max-w-[720px] px-3 py-4 sm:px-4 sm:py-6 flex flex-col gap-6">
      <h1 className="text-xl font-semibold tracking-tight">Settings</h1>

      <Section title="LLM Provider">
        <Field label="Provider">
          <select
            value={provider}
            onChange={(e) => {
              const val = e.target.value as typeof provider;
              setProvider(val);
              if (settings) {
                const p = settings.providers[val];
                setModel(p?.model || "");
                setBaseUrl(p?.base_url || "");
              }
            }}
            className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm outline-none focus:border-foreground/40"
          >
            <option value="gemini">Gemini</option>
            <option value="openai">OpenAI</option>
            <option value="anthropic">Anthropic</option>
          </select>
        </Field>
        <Field label="Model">
          <Input value={model} onChange={setModel} placeholder="gemini-2.0-flash" />
        </Field>
        <Field label="Base URL (optional)">
          <Input value={baseUrl} onChange={setBaseUrl} placeholder="https://api.openai.com/v1" />
        </Field>
        <Field label="API Key">
          <Input
            value={apiKey}
            onChange={setApiKey}
            placeholder={
              settings?.providers[provider]?.api_key_set
                ? "Key already set (type to replace)"
                : "Enter API key..."
            }
            type="password"
          />
        </Field>
        <button
          onClick={handleSave}
          disabled={saving}
          className="self-start rounded-md bg-foreground px-3 py-1.5 text-sm text-background hover:opacity-90 disabled:opacity-50"
        >
          {saving ? "Saving..." : "Save Settings"}
        </button>
        {msg && <span className="text-xs text-text-secondary">{msg}</span>}
      </Section>

      <Section title="Agent Network Configuration">
        <p className="text-xs text-text-secondary">
          Configure each agent to run locally or on a network PC. Network agents
          are not started by this system — they must be running on the remote
          host independently.
        </p>
        {AGENT_KEYS.map((key) => {
          const cfg = agentNetwork[key];
          const isNetwork = cfg.network_mode;
          const label = key.charAt(0).toUpperCase() + key.slice(1);
          return (
            <div key={key} className="flex flex-col gap-2">
              <div className="flex items-center gap-3">
                <button
                  type="button"
                  onClick={() => toggleNetwork(key)}
                  className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors ${
                    isNetwork ? "bg-blue-500" : "bg-green-500"
                  }`}
                >
                  <span
                    className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow ring-0 transition-transform ${
                      isNetwork ? "translate-x-4" : "translate-x-0"
                    }`}
                  />
                </button>
                <span className="text-sm font-medium">{label} Agent</span>
                <span
                  className={`text-[10px] uppercase tracking-wider px-1.5 py-0.5 rounded ${
                    isNetwork
                      ? "bg-blue-500/15 text-blue-400"
                      : "bg-green-500/15 text-green-400"
                  }`}
                >
                  {isNetwork ? "Network" : "Local"}
                </span>
              </div>
              {isNetwork && (
                <div className="flex gap-2 ml-12">
                  <div className="flex-1">
                    <span className="text-[10px] uppercase tracking-wider text-text-muted">
                      Host / IP
                    </span>
                    <Input
                      value={cfg.network_host}
                      onChange={(v) => updateNetworkHost(key, v)}
                      placeholder="192.168.1.101"
                    />
                  </div>
                  <div className="w-24">
                    <span className="text-[10px] uppercase tracking-wider text-text-muted">
                      Port
                    </span>
                    <Input
                      value={String(cfg.network_port)}
                      onChange={(v) => updateNetworkPort(key, v)}
                      placeholder={String(AGENT_DEFAULTS[key].port)}
                    />
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </Section>

      <Section title="Kaggle API">
        <p className="text-xs text-text-secondary">
          Required to fetch live datasets from Kaggle. Get your credentials from{" "}
          <a
            href="https://www.kaggle.com/settings"
            target="_blank"
            rel="noopener noreferrer"
            className="underline hover:text-foreground"
          >
            kaggle.com/settings
          </a>{" "}
          (API section → Create New Token).
        </p>
        <Field label="Kaggle Username">
          <Input value={kaggleUsername} onChange={setKaggleUsername} placeholder="yourusername" />
        </Field>
        <Field label="Kaggle API Key">
          <Input
            value={kaggleKey}
            onChange={setKaggleKey}
            placeholder={
              settings?.kaggle_key_set
                ? "Key already set (type to replace)"
                : "Paste your kaggle.json key..."
            }
            type="password"
          />
        </Field>
      </Section>

      <Section title="Theme">
        <div className="flex flex-wrap gap-2">
          {(
            [
              { v: null, label: "System" },
              { v: false, label: "Light" },
              { v: true, label: "Dark" },
            ] as const
          ).map((opt) => (
            <button
              key={String(opt.v)}
              onClick={() => setDarkMode(opt.v)}
              className={`rounded-md border px-3 py-1.5 text-sm transition-colors ${
                darkMode === opt.v
                  ? "border-foreground bg-foreground text-background"
                  : "border-border hover:bg-surface-hover"
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </Section>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-border bg-surface p-4 flex flex-col gap-4 sm:p-5">
      <h2 className="text-sm font-semibold">{title}</h2>
      {children}
    </div>
  );
}
function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="flex flex-col gap-1.5">
      <span className="text-[11px] uppercase tracking-wider text-text-muted">{label}</span>
      {children}
    </label>
  );
}
function Input({
  value,
  onChange,
  placeholder,
  type = "text",
}: {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  type?: string;
}) {
  return (
    <input
      type={type}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm outline-none focus:border-foreground/40"
    />
  );
}
