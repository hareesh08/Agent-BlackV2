import { useEffect, useRef, useState } from "react";
import mermaid from "mermaid";
import { useDarkMode } from "@/hooks/use-dark-mode";

const baseThemeVariables = {
  fontFamily: "monospace",
  fontSize: "13px",
};

interface MermaidDiagramProps {
  code: string;
  zoom?: number;
  onZoomChange?: (zoom: number) => void;
}

export function MermaidDiagram({ code, zoom = 1, onZoomChange }: MermaidDiagramProps) {
  const ref = useRef<HTMLDivElement>(null);
  const dragState = useRef<{ x: number; y: number; left: number; top: number } | null>(null);
  const [svg, setSvg] = useState("");
  const [error, setError] = useState("");
  const { isDark } = useDarkMode();

  useEffect(() => {
    if (!code || !ref.current) return;
    setError("");
    setSvg("");

    mermaid.initialize({
      startOnLoad: false,
      theme: isDark ? "dark" : "default",
      securityLevel: "loose",
      themeVariables: isDark
        ? {
            ...baseThemeVariables,
            primaryColor: "#4A90D9",
            primaryTextColor: "#e0e0e0",
            primaryBorderColor: "#e0e0e0",
            lineColor: "#666",
            secondaryColor: "#1a1a2e",
            tertiaryColor: "#16213e",
          }
        : {
            ...baseThemeVariables,
            primaryColor: "#4A90D9",
            primaryTextColor: "#1a1a1a",
            primaryBorderColor: "#1a1a1a",
            lineColor: "#555",
            secondaryColor: "#f5f5f5",
            tertiaryColor: "#ebebeb",
          },
    });

    const id = `mermaid-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
    mermaid.render(id, code).then(
      ({ svg }) => setSvg(svg),
      (err) => setError(String(err?.message || err)),
    );
  }, [code, isDark]);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.scrollTo({ left: 0, top: 0 });
  }, [code]);

  useEffect(() => {
    const el = ref.current;
    if (!el || !onZoomChange) return;
    const onWheel = (e: WheelEvent) => {
      if (e.ctrlKey || e.metaKey) {
        e.preventDefault();
        const delta = e.deltaY > 0 ? -0.1 : 0.1;
        onZoomChange(Math.min(5, Math.max(0.2, zoom + delta)));
      }
    };
    el.addEventListener("wheel", onWheel, { passive: false });
    return () => el.removeEventListener("wheel", onWheel);
  }, [zoom, onZoomChange]);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    const onPointerDown = (e: PointerEvent) => {
      if (e.button !== 0) return;
      dragState.current = {
        x: e.clientX,
        y: e.clientY,
        left: el.scrollLeft,
        top: el.scrollTop,
      };
      el.setPointerCapture?.(e.pointerId);
      el.style.cursor = "grabbing";
    };

    const onPointerMove = (e: PointerEvent) => {
      const drag = dragState.current;
      if (!drag) return;
      el.scrollLeft = drag.left - (e.clientX - drag.x);
      el.scrollTop = drag.top - (e.clientY - drag.y);
    };

    const stopDragging = (e: PointerEvent) => {
      if (!dragState.current) return;
      dragState.current = null;
      el.releasePointerCapture?.(e.pointerId);
      el.style.cursor = svg ? "grab" : "default";
    };

    el.addEventListener("pointerdown", onPointerDown);
    el.addEventListener("pointermove", onPointerMove);
    el.addEventListener("pointerup", stopDragging);
    el.addEventListener("pointercancel", stopDragging);
    el.addEventListener("pointerleave", stopDragging);

    el.style.cursor = svg ? "grab" : "default";

    return () => {
      el.removeEventListener("pointerdown", onPointerDown);
      el.removeEventListener("pointermove", onPointerMove);
      el.removeEventListener("pointerup", stopDragging);
      el.removeEventListener("pointercancel", stopDragging);
      el.removeEventListener("pointerleave", stopDragging);
      el.style.cursor = "default";
    };
  }, [svg]);

  if (error) {
    return (
      <div className="rounded-lg border border-red-500/30 bg-red-500/5 p-4">
        <p className="text-xs text-red-400 font-mono mb-2">Mermaid render error:</p>
        <pre className="text-xs text-text-secondary overflow-x-auto whitespace-pre-wrap">{error}</pre>
      </div>
    );
  }

  return (
    <div
      ref={ref}
      className="mermaid-diagram overflow-auto touch-none select-none"
    >
      <div
        className="flex min-w-max justify-center p-2 [&_svg]:h-auto [&_svg]:max-w-none [&_svg]:overflow-visible"
        style={{ transform: `scale(${zoom})`, transformOrigin: "top left" }}
        dangerouslySetInnerHTML={{ __html: svg }}
      />
    </div>
  );
}
