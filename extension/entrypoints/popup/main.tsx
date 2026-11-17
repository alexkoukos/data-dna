import { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import "@fontsource/plus-jakarta-sans/400.css";
import "@fontsource/plus-jakarta-sans/700.css";
import "@fontsource/plus-jakarta-sans/800.css";
import "../../src/ui.css";
import { getSettings, type DayStats, type RecentEvent } from "../../src/storage";

const WORD: Record<string, string> = {
  allow: "Allowed",
  mask: "Masked",
  warn: "Warned",
  local: "Answered locally",
  block: "Blocked",
};

const EMPTY: DayStats = { day: "", checked: 0, masked: 0, warned: 0, blocked: 0, local: 0 };

function Popup() {
  const [stats, setStats] = useState<DayStats>(EMPTY);
  const [recent, setRecent] = useState<RecentEvent[]>([]);
  const [version, setVersion] = useState<number | null>(null);
  const [who, setWho] = useState("");

  useEffect(() => {
    void (async () => {
      const {
        stats: s,
        recent: r,
        policy,
      } = await chrome.storage.local.get(["stats", "recent", "policy"]);
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
    <div className="wrap" style={{ width: 360, background: "var(--tint)" }}>
      <div className="row" style={{ justifyContent: "space-between" }}>
        <img className="wordmark" src="/brand/hive-wordmark.svg" alt="Hive" width={96} />
        <span className="muted status">{who ? `Signed in as ${who}` : "Not paired yet"}</span>
      </div>
      <p className="saves">
        <b>{stats.masked + stats.blocked + stats.local}</b>
        <span>{stats.masked + stats.blocked + stats.local === 1 ? "save" : "saves"} today</span>
      </p>
      <p className="muted" style={{ margin: "0 0 12px" }}>
        {stats.masked + stats.blocked + stats.local > 0
          ? "Nothing of the hive left."
          : "Paste into an AI chat and I'll check it first."}
      </p>
      <div className="grid" role="list" aria-label="Today">
        {[
          ["Checked", stats.checked],
          ["Masked", stats.masked],
          ["Warned", stats.warned],
          ["Blocked", stats.blocked],
        ].map(([label, n]) => (
          <div className="stat" role="listitem" key={label}>
            <b>{n}</b>
            <span>{label}</span>
          </div>
        ))}
      </div>
      <h2>Last events</h2>
      {recent.length === 0 ? (
        <p className="muted">Nothing yet. Each check shows up here.</p>
      ) : (
        <ul className="events">
          {recent.map((e) => (
            <li key={e.ts}>
              <span className={`tag ${e.action}`}>{WORD[e.action] ?? e.action}</span>
              <span>{e.tool}</span>
              <span className="muted" style={{ marginLeft: "auto" }}>
                {new Date(e.ts).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
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
          Refresh now
        </button>
      </p>
      <div className="row" style={{ marginTop: 8 }}>
        <button className="primary" onClick={openPanel} style={{ flex: 1 }}>
          Open Company AI
        </button>
        <button onClick={() => chrome.runtime.openOptionsPage()}>Settings</button>
      </div>
    </div>
  );
}

createRoot(document.getElementById("root")!).render(<Popup />);
