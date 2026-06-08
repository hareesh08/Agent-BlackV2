import { useEffect, useState } from "react";
import { useAppStore } from "@/lib/store";

export function useDarkMode() {
  const darkMode = useAppStore((s) => s.darkMode);
  const setDarkMode = useAppStore((s) => s.setDarkMode);
  const [systemDark, setSystemDark] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const mql = window.matchMedia("(prefers-color-scheme: dark)");
    const syncSystemPreference = () => setSystemDark(mql.matches);
    syncSystemPreference();

    mql.addEventListener("change", syncSystemPreference);
    return () => mql.removeEventListener("change", syncSystemPreference);
  }, []);

  const isDark = darkMode ?? systemDark;

  useEffect(() => {
    if (typeof document === "undefined") return;
    const apply = () => {
      document.documentElement.classList.toggle("dark", isDark);
    };

    apply();
  }, [isDark]);

  const toggle = () => setDarkMode(!isDark);
  return { darkMode, isDark, toggle, setDarkMode };
}
