import { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import "@fontsource/poppins/400.css";
import "@fontsource/poppins/700.css";
import "@fontsource/poppins/600.css";
import "@fontsource/playfair-display/600.css";
import "../../src/ui.css";
import { Link2, Save } from "lucide-react";
import { TextureStyles } from "../../src/TextureStyles";
import { pair, refreshPolicy } from "../../src/api";
import { getSettings, saveSettings } from "../../src/storage";

interface DemoUser {
  user: string;
  team: string;
}

function Options() {
  const [brainUrl, setBrainUrl] = useState("");
  const [code, setCode] = useState("");
  const [demoUser, setDemoUser] = useState("");
  const [paired, setPaired] = useState("");
  const [users, setUsers] = useState<DemoUser[]>([]);
  const [msg, setMsg] = useState("");

  useEffect(() => {
    void (async () => {
      const s = await getSettings();
      setBrainUrl(s.brainUrl);
      setDemoUser(s.demoUser);
      if (s.token) setPaired(s.userLabel || "this device");
      loadUsers(s.brainUrl);
    })();
  }, []);

  const loadUsers = (url: string) => {
    fetch(`${url.replace(/\/$/, "")}/v1/demo-users`)
      .then((r) => (r.ok ? r.json() : []))
      .then((u: DemoUser[]) => setUsers(u))
      .catch(() => setUsers([]));
  };

  const saveServer = async () => {
    await saveSettings({ brainUrl: brainUrl.trim() });
    loadUsers(brainUrl);
    await refreshPolicy();
    setMsg("Server address saved.");
  };

  const doPair = async () => {
    await saveSettings({ brainUrl: brainUrl.trim() });
    const res = await pair(code.trim());
    if (!res) {
      setMsg(
        "That code is wrong or has expired. Get a new one in the dashboard under Get the extension.",
      );
      return;
    }
    await saveSettings({ token: res.token, demoUser: "", userLabel: `${res.user} (${res.team})` });
    setPaired(`${res.user} (${res.team})`);
    setDemoUser("");
    setCode("");
    await refreshPolicy();
    setMsg("Paired. This browser now reports as that person.");
  };

  const pickDemo = async (user: string) => {
    setDemoUser(user);
    await saveSettings({ demoUser: user, token: "", userLabel: "" });
    setPaired("");
    await refreshPolicy();
    setMsg(user ? `Now acting as ${user}.` : "Demo user cleared.");
  };

  return (
    <>
      <TextureStyles />
      <div className="wrap" style={{ maxWidth: 640, margin: "0 auto" }}>
        <picture>
          <source media="(prefers-color-scheme: dark)" srcSet="/brand/hive-wordmark-dark.svg" />
          <img className="wordmark" src="/brand/hive-wordmark.svg" alt="Hive" width={120} />
        </picture>
        <h1 style={{ fontSize: 22, margin: "12px 0 4px" }}>Settings</h1>
        <p className="muted">
          In a company, IT sets this for you with a browser policy. These fields are for the demo.
        </p>

        <label htmlFor="server">Company server address</label>
        <div className="row">
          <input id="server" value={brainUrl} onChange={(e) => setBrainUrl(e.target.value)} />
          <button onClick={saveServer}>
            <Save size={16} aria-hidden="true" />
            Save
          </button>
        </div>

        <h2>Pair with the dashboard</h2>
        <p className="muted">
          Open the dashboard, go to Get the extension, and type the 6-digit code here.
        </p>
        <label htmlFor="code">Pairing code</label>
        <div className="row">
          <input
            id="code"
            inputMode="numeric"
            maxLength={6}
            value={code}
            onChange={(e) => setCode(e.target.value)}
          />
          <button className="primary" onClick={doPair} disabled={code.trim().length !== 6}>
            <Link2 size={16} aria-hidden="true" />
            Pair
          </button>
        </div>
        {paired && <p className="status">Paired as {paired}.</p>}

        <h2>Or pick a demo user</h2>
        <label htmlFor="demo">Act as</label>
        <select id="demo" value={demoUser} onChange={(e) => void pickDemo(e.target.value)}>
          <option value="">Nobody in particular</option>
          {users.map((u) => (
            <option key={u.user} value={u.user}>
              {u.user} ({u.team})
            </option>
          ))}
        </select>
        {msg && (
          <p role="status" className="status">
            {msg}
          </p>
        )}

        <h2>What we check and what we keep</h2>
        <div className="bubble">
          <p>
            <b>Checked:</b> the text you paste or send in an AI chat, before it is sent. First in
            your browser, then on your company&apos;s own server. It is never sent to Hive&apos;s
            makers or to any outside service.
          </p>
          <p>
            <b>Kept:</b> a record only when something was found: the kind of data, a masked preview
            such as GR••••0695, the decision and the reason. Never the full message, never the real
            values. Messages that match nothing are not stored anywhere.
          </p>
          <p>
            <b>Reported:</b> which AI sites you visit (the site name and the time) so the company
            can see which tools are in use. No page content.
          </p>
          <p>
            <b>Your name:</b> the dashboard shows a pseudonym and your team. Only two people
            together, with a written reason, can see who a pseudonym is, and every look is logged.
          </p>
          <p>
            <b>Why this exists:</b> the EU AI Act and GDPR ask companies to be open about
            monitoring. This is that page.
          </p>
        </div>
      </div>
    </>
  );
}

createRoot(document.getElementById("root")!).render(<Options />);
