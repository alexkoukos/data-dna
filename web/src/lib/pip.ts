/** Picture in picture for the companion, so Thyro stays on top of other tools while people work.
 * Chrome and Edge (116+): a real floating window we can render into. Safari and others: a small
 * floating video fed from a canvas. Anything else: no button. */

interface DocPip {
  requestWindow(opts?: { width?: number; height?: number }): Promise<Window>;
  window: Window | null;
}
const docPip = (): DocPip | undefined =>
  (window as unknown as { documentPictureInPicture?: DocPip }).documentPictureInPicture;

export type PipKind = "window" | "video" | null;

export function pipSupport(): PipKind {
  if (docPip()) return "window";
  if (typeof document !== "undefined" && document.pictureInPictureEnabled) return "video";
  return null;
}

/** Copies the page's styles into the floating window so the same components look the same. */
function copyStyles(target: Window) {
  for (const sheet of Array.from(document.styleSheets)) {
    try {
      const css = Array.from(sheet.cssRules)
        .map((r) => r.cssText)
        .join("\n");
      const style = target.document.createElement("style");
      style.textContent = css;
      target.document.head.appendChild(style);
    } catch {
      if (sheet.href) {
        const link = target.document.createElement("link");
        link.rel = "stylesheet";
        link.href = sheet.href;
        target.document.head.appendChild(link);
      }
    }
  }
}

/** Must be called from a click. Resolves to the new window, ready to render into. */
export async function openWindowPip(width = 340, height = 420): Promise<Window> {
  const api = docPip();
  if (!api) throw new Error("Picture in picture is not available here.");
  const win = await api.requestWindow({ width, height });
  copyStyles(win);
  win.document.body.style.margin = "0";
  win.document.body.style.background = "#faf7f4";
  return win;
}

export interface VideoPip {
  update(poseUrl: string, line: string): void;
  close(): void;
}

/** Fallback: draws Thyro and his sentence on a canvas and floats it as a video. Must be called from a click. */
export async function openVideoPip(
  poseUrl: string,
  line: string,
  onClosed: () => void,
): Promise<VideoPip> {
  const canvas = document.createElement("canvas");
  canvas.width = 480;
  canvas.height = 560;
  const ctx = canvas.getContext("2d")!;
  const img = new Image();
  let currentLine = line;
  let alive = true;
  img.src = poseUrl;
  await img.decode().catch(() => undefined);

  const draw = () => {
    if (!alive) return;
    ctx.fillStyle = "#faf7f4";
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(img, 40, 20, 400, 400);
    ctx.fillStyle = "#1a1713";
    ctx.font = "600 26px Commissioner, system-ui, sans-serif";
    ctx.textAlign = "center";
    const words = currentLine.split(" ");
    let row = "";
    let y = 470;
    for (const w of words) {
      const test = row ? `${row} ${w}` : w;
      if (ctx.measureText(test).width > 420 && row) {
        ctx.fillText(row, canvas.width / 2, y);
        row = w;
        y += 34;
      } else row = test;
    }
    ctx.fillText(row, canvas.width / 2, y);
    requestAnimationFrame(draw);
  };
  draw();

  const video = document.createElement("video");
  video.muted = true;
  video.srcObject = canvas.captureStream(30);
  await video.play();
  await video.requestPictureInPicture();
  video.addEventListener(
    "leavepictureinpicture",
    () => {
      alive = false;
      onClosed();
    },
    { once: true },
  );
  return {
    update(url, text) {
      if (img.src !== new URL(url, location.href).href) img.src = url;
      currentLine = text;
    },
    close() {
      alive = false;
      if (document.pictureInPictureElement) void document.exitPictureInPicture();
    },
  };
}
