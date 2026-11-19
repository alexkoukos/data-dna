import { cn } from "@/lib/utils";
import {
  TerminalAnimationBlinkingCursor,
  TerminalAnimationCommandBar,
  TerminalAnimationContainer,
  TerminalAnimationContent,
  TerminalAnimationOutput,
  TerminalAnimationRoot,
  TerminalAnimationTabList,
  TerminalAnimationTabTrigger,
  TerminalAnimationTrailingPrompt,
  TerminalAnimationWindow,
  type TabContent,
  type TerminalLine,
} from "@/components/ui/terminal-animation";

const GREEN = "text-[#86efac]";
const AMBER = "text-[#fbbf24]";
const RED = "text-[#fca5a5]";
const DIM = "text-stone-400";

/** How to get the extension: download, unzip, load it in Chrome, or build it from the repo. */
export const INSTALL_TABS: TabContent[] = [
  {
    label: "download",
    command: "curl -O http://localhost:3000/extension.zip",
    lines: [
      { text: "  % Total    % Received  Time", color: DIM, delay: 250 },
      { text: "100  904k  100  904k  0:00:01", color: DIM, delay: 300 },
      { text: "", delay: 80 },
      { text: "  Saved extension.zip", color: GREEN, delay: 250 },
    ],
  },
  {
    label: "unzip",
    command: "unzip extension.zip -d sentry-extension",
    lines: [
      { text: "  Archive:  extension.zip", color: DIM, delay: 200 },
      { text: "  inflating: sentry-extension/manifest.json", color: DIM, delay: 90 },
      { text: "  inflating: sentry-extension/background.js", color: DIM, delay: 90 },
      { text: "  inflating: sentry-extension/content-scripts/ai-sites.js", color: DIM, delay: 90 },
      { text: "", delay: 80 },
      { text: "  Done. The folder is sentry-extension", color: GREEN, delay: 250 },
    ],
  },
  {
    label: "chrome",
    command: "open chrome://extensions",
    lines: [
      { text: "", delay: 80 },
      { text: "  1. Turn on Developer mode (top right)", color: "text-stone-200", delay: 350 },
      { text: "  2. Choose Load unpacked", color: "text-stone-200", delay: 350 },
      { text: "  3. Pick the sentry-extension folder", color: "text-stone-200", delay: 350 },
      { text: "", delay: 80 },
      { text: "  Sentry is on. Open ChatGPT, Claude or Gemini.", color: GREEN, delay: 300 },
    ],
  },
  {
    label: "build",
    command: "make extension",
    lines: [
      { text: "", delay: 80 },
      { text: "  Building the extension with WXT...", color: DIM, delay: 350 },
      { text: "  Built extension/.output/chrome-mv3", color: GREEN, delay: 400 },
      { text: "  Load that folder in chrome://extensions", color: DIM, delay: 200 },
    ],
  },
];

/** What the extension's card says for each of the five outcomes (the same wording as the card). */
export const OUTCOME_TABS: TabContent[] = [
  {
    label: "allowed",
    command: 'paste "Team lunch on Friday, the budget is on track."',
    lines: [
      { text: "", delay: 80 },
      { text: "  Allowed", color: GREEN, delay: 300 },
      { text: "  Nothing sensitive found. It goes on to the AI tool.", color: DIM, delay: 250 },
    ],
  },
  {
    label: "masked",
    command: 'paste "Pay GR1601101250000000012300695"',
    lines: [
      { text: "", delay: 80 },
      { text: "  That's hive honey. I kept it in.", color: AMBER, delay: 300 },
      { text: "  I replaced a bank account number (IBAN) before", color: DIM, delay: 200 },
      { text: "  anything went to the AI tool: Pay [IBAN_1]", color: DIM, delay: 200 },
    ],
  },
  {
    label: "warned",
    command: 'paste "Maybe the client list from last week"',
    lines: [
      { text: "", delay: 80 },
      { text: "  Let's check this before it leaves.", color: AMBER, delay: 300 },
      { text: "  Your message may contain a client name.", color: DIM, delay: 200 },
      { text: "  [ Edit message ]   [ Send anyway ]", color: "text-stone-200", delay: 250 },
    ],
  },
  {
    label: "local",
    command: "paste <confidential board memo>",
    lines: [
      { text: "", delay: 80 },
      { text: "  Kept in the hive.", color: AMBER, delay: 300 },
      { text: "  This is confidential, so it was not sent.", color: DIM, delay: 200 },
      { text: "  [ Ask Company AI here ]", color: "text-stone-200", delay: 250 },
    ],
  },
  {
    label: "blocked",
    command: "attach salary-bands-RESTRICTED.pdf",
    lines: [
      { text: "", delay: 80 },
      { text: "  File not attached", color: RED, delay: 300 },
      { text: "  Marked RESTRICTED, so it stays inside the company.", color: DIM, delay: 200 },
      { text: "  [ Open company AI ]", color: "text-stone-200", delay: 250 },
    ],
  },
];

/** The animated terminal, dressed for Sentry: a dark window, amber tabs, tabs you can click. */
export function ExtensionTerminal({
  tabs,
  label,
  className,
}: {
  tabs: TabContent[];
  /** Names the terminal for screen readers. */
  label: string;
  className?: string;
}) {
  return (
    <TerminalAnimationRoot
      tabs={tabs}
      alwaysDark
      hideCursorOnComplete={false}
      aria-label={label}
      className={cn("term-dark relative flex w-full justify-center", className)}
    >
      <TerminalAnimationContainer className="max-w-none px-0 pt-0 md:px-0 md:pt-0">
        <TerminalAnimationWindow
          backgroundColor="#14110d"
          minHeight="17rem"
          animateOnVisible={false}
          className="rounded-xl outline-1 outline-white/15"
        >
          <TerminalAnimationContent className="px-4 py-4 sm:px-6 sm:py-5">
            <div className="flex items-center gap-2 leading-relaxed">
              <span className="font-mono text-xs text-stone-500 select-none sm:text-sm">$</span>
              <TerminalAnimationCommandBar
                className="break-all font-mono text-xs text-stone-100 sm:text-sm"
                cursor={<TerminalAnimationBlinkingCursor />}
              />
            </div>
            <TerminalAnimationOutput
              className="mt-1"
              renderLine={(line: TerminalLine, _i: number, visible: boolean) =>
                visible ? (
                  <div className="leading-relaxed">
                    <span
                      className={cn(
                        "whitespace-pre-wrap break-words font-mono text-xs sm:text-sm",
                        line.color ?? "text-stone-300",
                      )}
                    >
                      {line.text || " "}
                    </span>
                  </div>
                ) : null
              }
            />
            <TerminalAnimationTrailingPrompt className="mt-1 flex items-center gap-2 leading-relaxed">
              <span className="font-mono text-sm text-stone-500 select-none">$</span>
              <TerminalAnimationBlinkingCursor />
            </TerminalAnimationTrailingPrompt>
          </TerminalAnimationContent>

          <div className="flex justify-center px-3 pb-4">
            <TerminalAnimationTabList className="inline-flex max-w-full flex-wrap items-center justify-center gap-1 rounded-lg border border-white/15 bg-surface/5 p-1">
              {tabs.map((tab, i) => (
                <TerminalAnimationTabTrigger
                  className={cn(
                    "min-h-11 cursor-pointer rounded-md px-3.5 font-mono text-sm transition-colors duration-150",
                    "data-[state=active]:bg-amber-500 data-[state=active]:font-semibold data-[state=active]:text-stone-900",
                    "data-[state=inactive]:text-stone-300 data-[state=inactive]:hover:text-white",
                  )}
                  index={i}
                  key={tab.label}
                >
                  {tab.label}
                </TerminalAnimationTabTrigger>
              ))}
            </TerminalAnimationTabList>
          </div>
        </TerminalAnimationWindow>
      </TerminalAnimationContainer>
    </TerminalAnimationRoot>
  );
}
