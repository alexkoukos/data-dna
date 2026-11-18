import { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import "@fontsource/poppins/400.css";
import "@fontsource/poppins/700.css";
import "@fontsource/poppins/600.css";
import "@fontsource/playfair-display/600.css";
import "../../src/ui.css";
import { ActionIcon } from "../../src/ActionIcon";
import { MessageSquareText, RefreshCw, Settings } from "lucide-react";
import { TextureStyles } from "../../src/TextureStyles";
import { TrendChart } from "../../src/TrendChart";
import { weekSeries } from "../../src/history";
import { getSettings, type DayStats, type RecentEvent } from "../../src/storage";

const WORD: Record<string, string> = {
  allow: "Allowed",
  mask: "Masked",
  warn: "Warned",
  local: "Answered locally",
  block: "Blocked",
};

const TOOL: Record<string, string> = { ChatGPT: "#10a37f", Claude: "#c9623f", Gemini: "#4a7de0" };

function ago(ts: number): string {
  const m = Math.max(0, Math.round((Date.now() - ts) / 60000));
  if (m < 1) return "just now";
  if (m < 60) return `${m} min ago`;
  const h = Math.round(m / 60);
  return h < 24 ? `${h} h ago` : `${Math.round(h / 24)} d ago`;
}

/** One ring, split by what happened to everything checked today. The centre says how many saves. */
function Gauge({ stats }: { stats: DayStats }) {
  const R = 52;
  const C = 2 * Math.PI * R;
  const parts = [
    { key: "masked", n: stats.masked, label: "Masked" },
    { key: "warned", n: stats.warned, label: "Warned" },
    { key: "blocked", n: stats.blocked, label: "Blocked" },
    { key: "local", n: stats.local, label: "Local" },
  ];
  const flagged = parts.reduce((a, p) => a + p.n, 0);
  const total = Math.max(stats.checked, flagged);
  const saves = stats.masked + stats.blocked + stats.local;
  let offset = 0;
  return (
    <div className="gauge">
      <svg
        viewBox="0 0 130 130"
        role="img"
        aria-label={`${total} checked today, ${flagged} flagged`}
      >
        <circle cx="65" cy="65" r={R} className="ring-bg" />
        {total > 0 &&
          parts.map((p) => {
            const len = (p.n / total) * C;
            const el = (
              <circle
                key={p.key}
                cx="65"
                cy="65"
                r={R}
                className={`ring ${p.key}`}
                strokeDasharray={`${Math.max(len - 3, 0)} ${C}`}
                strokeDashoffset={-offset}
              />
            );
            offset += len;
            return p.n > 0 ? el : null;
          })}
      </svg>
      <div className="gauge-center">
        <b>{total}</b>
        <span>checked</span>
      </div>
      <ul className="legend" aria-label="What happened to them">
        {parts.map((p) => (
          <li key={p.key}>
            <span className={`dot ${p.key}`} aria-hidden="true" />
            <span>{p.label}</span>
            <b>{p.n}</b>
          </li>
        ))}
        <li className="saves-line">
          <span>{saves === 1 ? "1 save" : `${saves} saves`} today</span>
        </li>
      </ul>
    </div>
  );
}

/** Saves per day for the last week: one number, one flat chart. */
function WeekCard({ history }: { history: Record<string, number> }) {
  const week = weekSeries(history, new Date());
  const peak = week.data.indexOf(Math.max(...week.data));
  return (
    <div className="weekcard">
      <p className="week-top">
        <b>{week.total}</b>
        <span>{week.total === 1 ? "save" : "saves"} in the last 7 days</span>
      </p>
      <p className="muted week-sub">
        {week.total === 0
          ? "This fills in as I check what you paste."
          : `Busiest day: ${week.labels[peak]}, ${week.data[peak]}`}
      </p>
      <TrendChart
        data={week.data}
        labels={week.labels}
        accent="#f59e0b"
        unit="saves"
        height={140}
        summary={`Saves per day, last 7 days. ${week.total} in total.`}
      />
    </div>
  );
}

const EMPTY: DayStats = { day: "", checked: 0, masked: 0, warned: 0, blocked: 0, local: 0 };

function Popup() {
  const [stats, setStats] = useState<DayStats>(EMPTY);
  const [recent, setRecent] = useState<RecentEvent[]>([]);
  const [version, setVersion] = useState<number | null>(null);
  const [who, setWho] = useState("");
  const [history, setHistory] = useState<Record<string, number>>({});

  useEffect(() => {
    void (async () => {
      const {
        stats: s,
        recent: r,
        policy,
        history: h,
      } = await chrome.storage.local.get(["stats", "recent", "policy", "history"]);
      setHistory((h as Record<string, number>) ?? {});
      const today = new Date().toISOString().slice(0, 10);
      if (s && (s as DayStats).day === today) setStats(s as DayStats);
      setRecent((r as RecentEvent[]) ?? []);
      setVersion((policy as { version?: number } | undefined)?.version ?? null);
      const st = await getSettings();
      setWho(st.demoUser || (st.token ? "paired device" : ""));
    })();
  }, []);

  const openPanel = async () => {
    const win = await chrome.windows.getCurrent();
    if (win.id !== undefined) await chrome.sidePanel.open({ windowId: win.id });
    window.close();
  };

  return (
    <>
      <TextureStyles />
      <div className="wrap" style={{ width: 440, background: "var(--tint)" }}>
        <div className="row" style={{ justifyContent: "space-between" }}>
          <h1 className="sr-only">Hive</h1>
          <picture>
            <source media="(prefers-color-scheme: dark)" srcSet="/brand/hive-wordmark-dark.svg" />
            <img className="wordmark" src="/brand/hive-wordmark.svg" alt="Hive" width={120} />
          </picture>
          <span className="muted status">{who ? `Signed in as ${who}` : "Not paired yet"}</span>
        </div>
        <Gauge stats={stats} />
        <section aria-labelledby="week-h">
          <h2 id="week-h">This week</h2>
          <WeekCard history={history} />
        </section>
        <h2>Last events</h2>
        {recent.length === 0 ? (
          <p className="muted">Nothing yet. Each check shows up here.</p>
        ) : (
          <ul className="events">
            {recent.slice(0, 3).map((e) => (
              <li key={e.ts} className={`ev ${e.action}`}>
                <span
                  className="avatar"
                  style={{ background: TOOL[e.tool] ?? "#6b7280" }}
                  aria-hidden="true"
                >
                  {e.tool.slice(0, 1)}
                </span>
                <div className="ev-body">
                  <div className="ev-head">
                    <b>{e.tool}</b>
                    <span className="muted">{ago(e.ts)}</span>
                  </div>
                  {e.reason && <p className="ev-reason">{e.reason}</p>}
                </div>
                <span className={`tag ${e.action}`}>
                  <ActionIcon action={e.action} />
                  {WORD[e.action] ?? e.action}
                </span>
              </li>
            ))}
          </ul>
        )}
        <p className="muted status">
          Policy version {version ?? "not loaded yet"}{" "}
          <button
            type="button"
            onClick={async () => {
              const p = (await chrome.runtime.sendMessage({ type: "policy", force: true })) as {
                version?: number;
              } | null;
              setVersion(p?.version ?? null);
            }}
            style={{ minHeight: 44, marginLeft: 4 }}
          >
            <RefreshCw size={16} aria-hidden="true" />
            Refresh now
          </button>
        </p>
        <div className="row" style={{ marginTop: 8 }}>
          <button className="primary" onClick={openPanel} style={{ flex: 1 }}>
            <MessageSquareText size={16} aria-hidden="true" />
            Open Company AI
          </button>
          <button onClick={() => chrome.runtime.openOptionsPage()}>
            <Settings size={16} aria-hidden="true" />
            Settings
          </button>
        </div>
      </div>
    </>
  );
}

createRoot(document.getElementById("root")!).render(<Popup />);
