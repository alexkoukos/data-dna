import { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import "../../src/ui.css";
import { getSettings, type DayStats, type RecentEvent } from "../../src/storage";

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
    <div className="wrap" style={{ width: 340 }}>
      <div className="row" style={{ justifyContent: "space-between" }}>
        <h1>Pyli</h1>
        <span className="muted status">{who ? `Signed in as ${who}` : "Not paired yet"}</span>
      </div>
      <h2>Today</h2>
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
        <p className="muted">Nothing yet. Paste something into an AI chat and it shows up here.</p>
      ) : (
        <ul className="events">
          {recent.map((e) => (
            <li key={e.ts}>
              <span className={`tag ${e.action}`}>{e.action}</span>
              <span>{e.tool}</span>
              <span className="muted" style={{ marginLeft: "auto" }}>
                {new Date(e.ts).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
              </span>
            </li>
          ))}
        </ul>
      )}
      <p className="muted status">Policy version {version ?? "not loaded yet"}</p>
      <div className="row" style={{ marginTop: 8 }}>
        <button className="primary" onClick={openPanel} style={{ flex: 1 }}>
          Open company AI
        </button>
        <button onClick={() => chrome.runtime.openOptionsPage()}>Settings</button>
      </div>
    </div>
  );
}

createRoot(document.getElementById("root")!).render(<Popup />);
