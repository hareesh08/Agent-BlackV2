import { Link } from "@tanstack/react-router";
import { Menu, Moon, Sun } from "lucide-react";
import { useAppStore } from "@/lib/store";
import { useDarkMode } from "@/hooks/use-dark-mode";
import { StatusDot } from "@/components/shared/StatusDot";

const GITHUB_URL = "https://github.com/hareesh08/Agent-BlackV2";

export function Header() {
  const setDrawerOpen = useAppStore((s) => s.setDrawerOpen);
  const { isDark, toggle } = useDarkMode();

  return (
    <header className="sticky top-0 z-40 border-b border-border bg-background/80 backdrop-blur-md">
      <div className="flex h-12 items-center gap-3 px-3 sm:h-14 sm:px-4">
        <button
          onClick={() => setDrawerOpen(true)}
          className="rounded-md p-2 text-foreground hover:bg-surface-hover transition-colors"
          aria-label="Open menu"
        >
          <Menu className="h-5 w-5" />
        </button>

        <Link to="/" className="flex items-center gap-2 group">
          <div className="h-6 w-6 rounded-md bg-foreground flex items-center justify-center">
            <span className="text-[10px] font-bold text-background tracking-tighter">A·B</span>
          </div>
          <span className="text-xs font-semibold tracking-tight sm:text-sm">
            Agent Black
          </span>
          <sup className="hidden sm:inline text-[9px] font-medium text-text-muted tracking-wide ml-0.5 mt-0.5">
            TM
          </sup>
        </Link>

        <div className="ml-3 hidden sm:flex items-center gap-2 text-xs text-text-secondary">
          <StatusDot status="online" />
          <span>online</span>
        </div>

        <div className="ml-auto flex items-center gap-1">
          <a
            href={GITHUB_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="hidden sm:inline-flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-[11px] font-medium text-text-secondary hover:bg-surface-hover hover:text-foreground transition-colors"
          >
            <svg viewBox="0 0 16 16" fill="currentColor" className="h-3.5 w-3.5">
              <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z" />
            </svg>
            <span className="hidden md:inline">GitHub</span>
          </a>
          <button
            onClick={toggle}
            className="rounded-md p-2 text-foreground hover:bg-surface-hover transition-colors"
            aria-label="Toggle theme"
          >
            {isDark ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
          </button>
        </div>
      </div>
    </header>
  );
}
