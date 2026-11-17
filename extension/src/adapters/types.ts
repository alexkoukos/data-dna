/**
 * One adapter per AI site. Every DOM selector lives in an adapter and nowhere else, so a site
 * redesign means editing one file.
 */
export interface Adapter {
  id: string;
  /** Name used in telemetry and the inventory, e.g. "ChatGPT". */
  tool: string;
  matches(url: URL): boolean;
  getComposer(): HTMLElement | null;
  getText(): string;
  /** Replaces the composer text in a way the site's own framework notices. */
  setText(text: string): boolean;
  getSendButton(): HTMLElement | null;
  /** Element that holds the AI's answers. */
  responseRoot(): HTMLElement;
}
