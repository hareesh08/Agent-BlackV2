import { useEffect, useRef, useState } from "react";

export function useLiveUptime(serverUptime: number | null) {
  const [display, setDisplay] = useState("00:00:00");
  const baseRef = useRef(0);
  const tickRef = useRef<number | null>(null);

  useEffect(() => {
    if (serverUptime == null) return;
    baseRef.current = serverUptime;
    setDisplay(format(serverUptime));

    tickRef.current = window.setInterval(() => {
      baseRef.current += 1;
      setDisplay(format(baseRef.current));
    }, 1000);

    return () => {
      if (tickRef.current) clearInterval(tickRef.current);
    };
  }, [serverUptime]);

  return display;
}

function format(s: number): string {
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = Math.floor(s % 60);
  return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}:${String(sec).padStart(2, "0")}`;
}
