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
