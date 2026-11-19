import { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import "@fontsource/poppins/400.css";
import "@fontsource/poppins/700.css";
import "@fontsource/poppins/600.css";
import "@fontsource/space-grotesk/600.css";
import "../../src/ui.css";
import { Logo } from "../../src/Logo";
import { ActionIcon } from "../../src/ActionIcon";
import { ExternalLink, MessageSquareText, Settings } from "lucide-react";
import { TextureStyles } from "../../src/TextureStyles";
import { getSettings, type DayStats, type RecentEvent } from "../../src/storage";
import { ShieldCheck } from "lucide-react";

const WORD: Record<string, string> = {
  allow: "Allowed",
  mask: "Masked",
  warn: "Warned",
  local: "Answered locally",
  block: "Blocked",
};

/** Each tool's colour and a white logo bundled with the extension, so the list works offline and no site is contacted. */
const TOOL: Record<string, { color: string; logo: string }> = {
  ChatGPT: { color: "#10a37f", logo: "/logos/chatgpt.svg" },
  "Claude.ai": { color: "#c9623f", logo: "/logos/claude.svg" },
  Gemini: { color: "#4a7de0", logo: "/logos/gemini.svg" },
  "Mock AI (demo)": { color: "#2a2520", logo: "/brand/sentry-guard.svg" },
};

/** The tool's logo on its own colour. A tool without a logo falls back to its first letter. */
function ToolAvatar({ tool }: { tool: string }) {
  const t = TOOL[tool];
  return (
    <span className="avatar" style={{ background: t?.color ?? "#6b7280" }} aria-hidden="true">
      {t ? <img src={t.logo} alt="" className="avatar-logo" /> : tool.slice(0, 1)}
    </span>
  );
}

function ago(ts: number): string {
  const m = Math.max(0, Math.round((Date.now() - ts) / 60000));
  if (m < 1) return "just now";
  if (m < 60) return `${m} min ago`;
  const h = Math.round(m / 60);
  return h < 24 ? `${h} h ago` : `${Math.round(h / 24)} d ago`;
}

/** The dashboard is on the same machine as the brain, one port over. */
async function dashboardUrl(): Promise<string> {
  try {
    const u = new URL((await getSettings()).brainUrl);
    u.port = "3000";
    u.pathname = "/security";
    return u.toString();
  } catch {
    return "http://localhost:3000/security";
  }
}

/** Small on purpose: who is signed in, the last few checks, and where to go next. The numbers live on the dashboard. */
function Popup() {
  const [recent, setRecent] = useState<RecentEvent[]>([]);
  const [who, setWho] = useState("");
  const [stats, setStats] = useState<DayStats | null>(null);

  useEffect(() => {
    void (async () => {
      const { recent: r, stats: d } = await chrome.storage.local.get(["recent", "stats"]);
      setRecent((r as RecentEvent[]) ?? []);
      const day = d as DayStats | undefined;
      if (day && day.day === new Date().toISOString().slice(0, 10)) setStats(day);
      const st = await getSettings();
      setWho(st.userLabel || st.demoUser || (st.token ? "paired device" : ""));
    })();
  }, []);

  // The worker connects in the background right after install: show it the moment it happens.
  useEffect(() => {
    const onChange = (c: Record<string, chrome.storage.StorageChange>, area: string) => {
      if (area !== "local" || !c.settings) return;
      void getSettings().then((st) =>
        setWho(st.userLabel || st.demoUser || (st.token ? "paired device" : "")),
      );
    };
    chrome.storage.onChanged.addListener(onChange);
    return () => chrome.storage.onChanged.removeListener(onChange);
  }, []);

  const [trying, setTrying] = useState(false);
  const [failed, setFailed] = useState(false);
  const connect = async () => {
    setTrying(true);
    setFailed(false);
    const r = (await chrome.runtime.sendMessage({ type: "connect" })) as { ok: boolean } | null;
    const st = await getSettings();
    setWho(st.userLabel || st.demoUser || (st.token ? "paired device" : ""));
    setFailed(!r?.ok);
    setTrying(false);
  };

  const openPanel = async () => {
    const win = await chrome.windows.getCurrent();
    if (win.id !== undefined) await chrome.sidePanel.open({ windowId: win.id });
    window.close();
  };
  const openDashboard = async () => {
    await chrome.tabs.create({ url: await dashboardUrl() });
    window.close();
  };

  return (
    <>
      <TextureStyles />
      <div className="wrap" style={{ width: 380, background: "var(--tint)" }}>
        <div className="row" style={{ justifyContent: "space-between" }}>
          <h1 className="sr-only">Sentry</h1>
          <Logo />
          <span className="muted status">{who ? `Connected as ${who}` : "Not connected"}</span>
        </div>
        {who ? null : (
          <div className="connect-card" role="status">
            <b>Not connected to a Sentry server.</b>
            <span className="muted">
              {failed
                ? "Still can't reach it. Start it with “docker compose up”, then try again."
                : "Start the server (“docker compose up”), then press Connect."}
            </span>
            <button
              className="primary"
              type="button"
              onClick={() => void connect()}
              disabled={trying}
            >
              {trying ? "Connecting…" : "Connect"}
            </button>
          </div>
        )}
        <div className="shield-strip" role="status">
          <ShieldCheck size={20} aria-hidden="true" />
          <div>
            <b>Protection is on</b>
            <span className="muted">
              {stats && stats.checked > 0
                ? `${stats.checked} checked today, ${stats.masked + stats.blocked + stats.local} kept inside`
                : "Checking what you send to AI tools"}
            </span>
          </div>
        </div>
        <h2>Last events</h2>
        {recent.length === 0 ? (
          <p className="muted">Nothing yet. Each check shows up here.</p>
        ) : (
          <ul className="events">
            {recent.slice(0, 3).map((e) => (
              <li key={e.ts} className={`ev ${e.action}`}>
                <ToolAvatar tool={e.tool} />
                <div className="ev-body">
                  <div className="ev-head">
                    <b>{e.tool}</b>
                    <span className="muted">{ago(e.ts)}</span>
                  </div>
                  <span className={`tag ${e.action}`}>
                    <ActionIcon action={e.action} />
                    {WORD[e.action] ?? e.action}
                  </span>
                </div>
              </li>
            ))}
          </ul>
        )}
        <div className="row actions-row" style={{ marginTop: 12 }}>
          <button className="primary glow" onClick={openPanel}>
            <MessageSquareText size={16} aria-hidden="true" />
            Company AI
          </button>
          <button className="glow soft" onClick={() => void openDashboard()}>
            <ExternalLink size={16} aria-hidden="true" />
            Dashboard
          </button>
          <button
            className="glow soft icon-only"
            onClick={() => chrome.runtime.openOptionsPage()}
            aria-label="Settings"
          >
            <Settings size={16} aria-hidden="true" />
          </button>
        </div>
      </div>
    </>
  );
}

document.body.classList.add("fit");
createRoot(document.getElementById("root")!).render(<Popup />);
