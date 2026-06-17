import { create } from "zustand";
import { persist } from "zustand/middleware";

export type AgentKey = "research" | "solution" | "experiment";

export type SectionValue = string | StructuredSection | null | undefined;

export interface StructuredSection {
  text?: string;
  papers?: PaperEntry[];
  items?: SectionItem[];
  phases?: PhaseEntry[];
  special_considerations?: string[];
  tech_stack_notes?: string[];
  key_concepts?: Record<string, unknown>;
  [key: string]: unknown;
}

export interface PaperEntry {
  title?: string;
  authors?: string | string[];
  year?: number | string;
  venue?: string;
  key_finding?: string;
  relevance?: string;
  description?: string;
  url?: string;
  [key: string]: unknown;
}

export interface SectionItem {
  name?: string;
  metric?: string;
  type?: string;
  purpose?: string;
  domain?: string;
  size?: string;
  source?: string;
  license?: string;
  suitable_for?: string;
  libraries?: string[];
  pros?: string[];
  cons?: string[];
  when_to_use?: string;
  target?: string;
  calculation?: string;
  threshold_or_goal?: string;
  url?: string;
  description?: string;
  [key: string]: unknown;
}

export interface PhaseEntry {
  phase?: string;
  weeks?: string;
  goal?: string;
  tasks?: string[];
  tech?: string[];
  deliverable?: string;
  [key: string]: unknown;
}

export interface ReportSections {
  error?: string | null;
  message?: string | null;
  reason?: string | null;
  suggestion?: string | null;
  supported_topics?: unknown;
  validation?: unknown;
  tech_stack?: string[];
  parse_warning?: string;
  literature_review?: SectionValue;
  datasets?: SectionValue;
  models?: SectionValue;
  evaluation_plan?: SectionValue;
  prototype_guidance?: SectionValue;
}

export interface TaskEvent {
  step: string;
  status: string;
  detail: string;
  timestamp: number;
}

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: number;
  query?: string;
  queryId?: number;
  taskId?: string;
  sections?: ReportSections;
  agentsUsed?: string[];
  reasoning?: string;
  pending?: boolean;
  taskProgress?: TaskEvent[];
  streamingContent?: string;
  raw?: unknown;
}

interface AppState {
  messages: Message[];
  addMessage: (m: Message) => void;
  updateMessage: (id: string, partial: Partial<Message>) => void;
  replaceAllMessages: (msgs: Message[]) => void;
  clearMessages: () => void;
  darkMode: boolean | null; // null = system
  setDarkMode: (v: boolean | null) => void;
  drawerOpen: boolean;
  setDrawerOpen: (v: boolean) => void;
  provider: "gemini" | "openai" | "anthropic";
  setProvider: (p: AppState["provider"]) => void;
}

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      messages: [],
      addMessage: (m) => set((s) => ({ messages: [...s.messages, m] })),
      updateMessage: (id, partial) =>
        set((s) => ({
          messages: s.messages.map((msg) =>
            msg.id === id ? { ...msg, ...partial } : msg,
          ),
        })),
      replaceAllMessages: (msgs) => set({ messages: msgs }),
      clearMessages: () => set({ messages: [] }),
      darkMode: null,
      setDarkMode: (v) => set({ darkMode: v }),
      drawerOpen: false,
      setDrawerOpen: (v) => set({ drawerOpen: v }),
      provider: "gemini",
      setProvider: (p) => set({ provider: p }),
    }),
    {
      name: "agent-black-store",
      partialize: (s) => ({
        darkMode: s.darkMode,
        provider: s.provider,
      }),
    },
  ),
);
