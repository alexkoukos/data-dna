import type { CSSProperties } from "react";
import { PHASE, PHASES } from "./loop";
import { OUTCOME_LABEL, SCENES, type Scene, type Seg } from "./scenes";

// One browser window on the laptop screen (720 x 450 design pixels). It is drawn from
// (scene, phase) alone, so the same component renders the loop and the still frames.

type Props = {
  scene: number;
  phase: number;
  /** Still frame: no cursor, no motion, the bee rests where it ended. */
  still?: boolean;
};

const px = ([x, y]: [number, number]) => `translate(${x}px, ${y}px)`;

function Pill({ kind, children }: { kind: "mask" | "block"; children: string }) {
  return <span className={`pill pill-${kind}`}>{children}</span>;
}

function Value({
  seg,
  swapped,
  flagged,
  kind,
}: {
  seg: Seg;
  swapped: boolean;
  flagged: boolean;
  kind: "mask" | "block";
}) {
  if (typeof seg === "string") return <>{seg}</>;
  return (
    <span className={`value${flagged ? " is-flagged" : ""}${swapped ? " is-swapped" : ""}`}>
      <span className="value-raw">{seg.raw}</span>
      <span className="value-pill" aria-hidden={!swapped}>
        <Pill kind={kind}>{seg.pill}</Pill>
      </span>
    </span>
  );
}

function BeeCardView({
  scene,
  outcomeKind,
}: {
  scene: Scene;
  outcomeKind: "mask" | "block" | "local";
}) {
  const c = scene.card;
  return (
    <div className="bee-card">
      <p className="bee-card-head">{c.headline}</p>
      <p className="bee-card-body">{c.body}</p>
      {c.rewrite ? <p className="bee-card-quote">{c.rewrite}</p> : null}
      <div className="bee-card-meta">
        <span className={`chip chip-${outcomeKind}`}>
          <span className="chip-icon" aria-hidden="true">
            {outcomeKind === "mask" ? "◐" : outcomeKind === "block" ? "■" : "⌂"}
          </span>
          {OUTCOME_LABEL[scene.outcome]}
        </span>
        <span className="bee-card-why">Why?</span>
      </div>
      <p className="bee-card-tip">{c.tip}</p>
      <div className="bee-card-actions">
        <span className="bc-btn bc-primary">{c.primary}</span>
        <span className="bc-btn bc-secondary">{c.secondary}</span>
      </div>
    </div>
  );
}

export function Screen({ scene: sceneIndex, phase, still = false }: Props) {
  const scene = SCENES[sceneIndex % SCENES.length];
  const id = PHASES[phase].id;
  const typed = phase >= PHASE.type;
  const pasted = phase >= PHASE.paste;
  const flagged = phase >= PHASE.bee;
  const swapped = phase >= PHASE.card;
  const carded = phase >= PHASE.card;
  const pillKind = scene.outcome === "mask" ? "mask" : "block";
  const stopped = carded && scene.outcome === "block";
  const saves = sceneIndex + (carded ? 1 : 0);

  const cursor =
    phase <= PHASE.idle
      ? ([560, 150] as [number, number])
      : phase === PHASE.type
        ? scene.geo.cursorType
        : phase === PHASE.paste
          ? ([scene.geo.cursorType[0] + 40, scene.geo.cursorType[1] - 30] as [number, number])
          : phase === PHASE.bee
            ? ([scene.geo.bee[0] + 60, scene.geo.bee[1] + 70] as [number, number])
            : scene.geo.cursorCard;

  const beeVars = {
    "--bx": `${scene.geo.bee[0]}px`,
    "--by": `${scene.geo.bee[1]}px`,
    "--px": `${scene.geo.perch[0]}px`,
    "--py": `${scene.geo.perch[1]}px`,
  } as CSSProperties;

  return (
    <div
      className={`screen${still ? " is-still" : ""}`}
      data-phase={id}
      data-scene={scene.id}
      style={beeVars}
    >
      <div className="chrome" aria-hidden="true">
        <span className="dots">
          <i />
          <i />
          <i />
        </span>
        <span className="tab">{scene.site.tab}</span>
        <span className="url">
          <span className="url-lock">▮</span>
          {scene.site.host}/chat
        </span>
        <span className="tools">
          <img className="ext-icon" src="/brand/hive-app-icon.svg" alt="" />
          <span className="badge" key={saves}>
            {saves} {saves === 1 ? "save" : "saves"} today
          </span>
        </span>
      </div>

      <div className="page" key={scene.id}>
        <div className="site-head" aria-hidden="true">
          <span className="site-logo" />
          <span className="site-name">{scene.site.name}</span>
          <span className="site-new">New chat</span>
        </div>
        <div className="thread" aria-hidden="true">
          <div className="msg-ai">Hi! Paste something or ask me anything.</div>
        </div>

        <div className="dock">
          <div className={`composer${stopped ? " is-stopped" : ""}`}>
            <div className={`line prompt${typed ? " is-in" : ""}`}>{scene.prompt}</div>
            {scene.file ? (
              <div className={`file${pasted ? " is-in" : ""}`}>
                <span className="file-icon">PDF</span>
                <span>
                  <strong>{scene.file.name}</strong>
                  <small>{scene.file.meta}</small>
                </span>
              </div>
            ) : (
              <div className={`paste${scene.mono ? " is-mono" : ""}${pasted ? " is-in" : ""}`}>
                {scene.paste.map((line, i) => (
                  <div
                    key={i}
                    className={`paste-line${line.length === 3 ? " is-row" : ""}${i === 0 && scene.id === "payroll" ? " is-head" : ""}`}
                  >
                    {line.map((seg, j) => (
                      <span key={j}>
                        <Value seg={seg} swapped={swapped} flagged={flagged} kind={pillKind} />
                      </span>
                    ))}
                  </div>
                ))}
              </div>
            )}
            <div className="composer-bar">
              <span className="attach" />
              <span className={`send${stopped ? " is-off" : ""}`}>
                {stopped ? "Stopped" : "Send"}
              </span>
            </div>
            <div className={`bee-card-wrap${carded ? " is-in" : ""}`}>
              <BeeCardView scene={scene} outcomeKind={scene.outcome} />
            </div>
          </div>
        </div>
      </div>

      <img className="bee" src="/brand/hive-guard-bee.svg" alt="" />
      {still ? null : (
        <svg
          className="cursor"
          style={{ transform: px(cursor) }}
          width="18"
          height="22"
          viewBox="0 0 18 22"
          aria-hidden="true"
        >
          <path
            d="M2 1.5v16l4.2-3.9 3 6.6 3-1.4-3-6.4h6z"
            fill="#262626"
            stroke="#fff"
            strokeWidth="1.5"
            strokeLinejoin="round"
          />
        </svg>
      )}
    </div>
  );
}
