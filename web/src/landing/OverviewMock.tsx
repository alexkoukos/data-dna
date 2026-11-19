// A static picture of the security Overview, drawn in Sentry colours. Demo data only.
const KPIS = [
  { label: "Saves this week", value: "1,284", note: "Nothing of the sentry left" },
  { label: "Handled without an AI model", value: "90%", note: "Fast checks, no tokens spent" },
  { label: "Unapproved AI tools in use", value: "5", note: "See which" },
];

const TEAMS = [
  { team: "Sales", tool: "AI Chat (personal)", count: 14, kind: "mask", word: "Masked" },
  { team: "Finance", tool: "Ask AI", count: 9, kind: "block", word: "Blocked" },
  { team: "Engineering", tool: "Code Helper", count: 6, kind: "block", word: "Blocked" },
] as const;

export function OverviewMock() {
  return (
    <div className="ov" role="group" aria-label="Security Overview, demo data">
      <p className="ov-demo">Demo data · the people and numbers here are invented</p>
      <div className="ov-kpis">
        {KPIS.map((k) => (
          <div key={k.label} className="ov-kpi">
            <p className="ov-kpi-label">{k.label}</p>
            <p className="ov-kpi-value">{k.value}</p>
            <p className="ov-kpi-note">{k.note}</p>
          </div>
        ))}
      </div>
      <div className="ov-table">
        <p className="ov-table-head">Client data sent to unapproved AI tools, this week</p>
        {TEAMS.map((t) => (
          <div key={t.team} className="ov-row">
            <span className="ov-team">{t.team}</span>
            <span className="ov-tool">{t.tool}</span>
            <span className="ov-count">{t.count}</span>
            <span className={`chip chip-${t.kind}`}>
              <span className="chip-icon" aria-hidden="true">
                {t.kind === "mask" ? "◐" : "■"}
              </span>
              {t.word}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
