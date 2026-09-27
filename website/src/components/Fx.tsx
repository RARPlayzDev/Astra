import { useEffect, useRef, useState } from "react";

/** Guard: never animate for users who asked for less motion. */
function reducedMotion(): boolean {
  return typeof window !== "undefined" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

/* ═══════════════ Preloader — brand wipe, once per session ═══════════════ */
export function Preloader() {
  const [seen] = useState(() => {
    if (typeof window === "undefined") return false;
    try { return !!sessionStorage.getItem("astra.pre"); } catch { return false; }
  });
  const [gone, setGone] = useState(false);
  const [done, setDone] = useState(false);

  useEffect(() => {
    if (seen || reducedMotion()) { setGone(true); return; }
    try { sessionStorage.setItem("astra.pre", "1"); } catch { /* ignore */ }
    const t1 = setTimeout(() => setDone(true), 1400);
    const t2 = setTimeout(() => setGone(true), 2100);
    return () => { clearTimeout(t1); clearTimeout(t2); };
  }, [seen]);

  if (seen || gone) return null;
  return (
    <div className={"preload" + (done ? " done" : "")} aria-hidden>
      <div className="preload-inner">
        <div className="preload-word">
          {"ASTRA".split("").map((ch, i) => (
            <span key={i} style={{ animationDelay: `${0.06 + i * 0.07}s` }}>{ch}</span>
          ))}
        </div>
        <div className="pline"><i /></div>
        <div className="preload-sub">ADAPTIVE SPECTRUM THREAT RECOGNITION</div>
      </div>
    </div>
  );
}

/* ═══════════════ Cursor — dot + trailing ring (desktop, motion OK) ═══════════════ */
export function CursorFollower() {
  const [active, setActive] = useState(false);
  const dotRef = useRef<HTMLDivElement>(null);
  const ringRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (reducedMotion()) return;
    if (window.matchMedia("(pointer: coarse)").matches) return;
    setActive(true);
  }, []);

  useEffect(() => {
    if (!active) return;
    const dot = dotRef.current;
    const ring = ringRef.current;
    if (!dot || !ring) return;

    let x = -100, y = -100, rx = -100, ry = -100, raf = 0, seen = false;

    const move = (e: MouseEvent) => {
      x = e.clientX; y = e.clientY;
      if (!seen) { seen = true; rx = x; ry = y; dot.style.opacity = ring.style.opacity = "1"; }
      dot.style.transform = `translate3d(${x}px, ${y}px, 0) translate(-50%, -50%)`;
      const hot = (e.target as HTMLElement)?.closest?.("a, button, summary, [data-cursor]");
      ring.classList.toggle("hot", !!hot);
    };
    const loop = () => {
      rx += (x - rx) * 0.16;
      ry += (y - ry) * 0.16;
      ring.style.transform = `translate3d(${rx}px, ${ry}px, 0) translate(-50%, -50%)`;
      raf = requestAnimationFrame(loop);
    };
    window.addEventListener("mousemove", move, { passive: true });
    raf = requestAnimationFrame(loop);
    return () => {
      window.removeEventListener("mousemove", move);
      cancelAnimationFrame(raf);
    };
  }, [active]);

  if (!active) return null;
  return (
    <>
      <div ref={dotRef} className="cursor-dot" style={{ opacity: 0 }} aria-hidden />
      <div ref={ringRef} className="cursor-ring" style={{ opacity: 0 }} aria-hidden />
    </>
  );
}

/* ═══════════════ CountUp — ticks from 0 when scrolled into view ═══════════════ */
export function CountUp({ to, decimals = 0, duration = 950 }: {
  to: number; decimals?: number; duration?: number;
}) {
  const [v, setV] = useState(to);           // SSR / first paint shows the final value
  const ref = useRef<HTMLSpanElement>(null);
  const fired = useRef(false);

  useEffect(() => {
    const el = ref.current;
    if (!el || reducedMotion()) return;
    const obs = new IntersectionObserver((entries) => {
      for (const e of entries) {
        if (!e.isIntersecting || fired.current) continue;
        fired.current = true;
        const start = performance.now();
        const tick = (now: number) => {
          const p = Math.min(1, (now - start) / duration);
          setV(to * (1 - Math.pow(1 - p, 3)));
          if (p < 1) requestAnimationFrame(tick);
          else setV(to);
        };
        requestAnimationFrame(tick);
      }
    }, { threshold: 0.35 });
    obs.observe(el);
    return () => obs.disconnect();
  }, [to, duration]);

  return <span ref={ref}>{v.toFixed(decimals)}</span>;
}

/* ═══════════════ Scramble — glyphs resolve into text on mount ═══════════════ */
export function Scramble({ text, className = "" }: { text: string; className?: string }) {
  const [out, setOut] = useState(text);
  useEffect(() => {
    if (reducedMotion()) return;
    const glyphs = "\u25A0\u25AA\u2593ABCDEF0123456789/:";
    const total = 30;
    let frame = 0;
    let raf = 0;
    const step = () => {
      frame += 1;
      const reveal = Math.floor((frame / total) * text.length);
      let s = "";
      for (let i = 0; i < text.length; i++) {
        if (i < reveal || text[i] === " ") s += text[i];
        else s += glyphs[Math.floor(Math.random() * glyphs.length)];
      }
      setOut(s);
      if (frame < total) raf = requestAnimationFrame(step);
      else setOut(text);
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }, [text]);
  return <span className={className}>{out}</span>;
}

/* ═══════════════ PageWipe — overlay sweep on internal navigation ═══════════════ */
export function PageWipe() {
  const [on, setOn] = useState(false);
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (e.defaultPrevented || e.button !== 0 ||
          e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
      const a = (e.target as HTMLElement | null)?.closest?.("a[href]") as HTMLAnchorElement | null;
      if (!a || a.target === "_blank" || a.hasAttribute("download")) return;
      let url: URL;
      try { url = new URL(a.href, location.href); } catch { return; }
      if (url.origin !== location.origin) return;
      if (url.pathname === location.pathname && url.hash) return;   // in-page anchor
      if (reducedMotion()) return;
      e.preventDefault();
      setOn(true);
      const href = url.href;
      setTimeout(() => { location.href = href; }, 430);
    };
    document.addEventListener("click", handler);
    return () => document.removeEventListener("click", handler);
  }, []);
  return <div className={"page-wipe" + (on ? " on" : "")} aria-hidden />;
}

/* ═══════════════ SectionDots — chapter rail for long pages ═══════════════ */
export function SectionDots({ items }: { items: [string, string][] }) {
  const [active, setActive] = useState(0);
  useEffect(() => {
    const els = items
      .map(([id]) => document.getElementById(id))
      .filter((el): el is HTMLElement => !!el);
    const obs = new IntersectionObserver((entries) => {
      for (const e of entries) {
        if (!e.isIntersecting) continue;
        const i = items.findIndex(([id]) => id === e.target.id);
        if (i >= 0) setActive(i);
      }
    }, { rootMargin: "-45% 0px -50% 0px" });
    els.forEach((el) => obs.observe(el));
    return () => obs.disconnect();
  }, [items]);

  return (
    <nav className="sec-dots" aria-label="Page sections">
      {items.map(([id, label], i) => (
        <button
          key={id}
          type="button"
          data-label={label}
          className={i === active ? "on" : ""}
          onClick={() => document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" })}
          aria-label={label}
        ><i /></button>
      ))}
    </nav>
  );
}
