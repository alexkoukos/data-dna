/**
 * Prepare an attached image for a vision model. The picture is redrawn in this browser on a white
 * page, at most 2048 pixels on its longest side, and saved again as JPEG:
 * - the model gets what a person sees: pixels hidden under transparency are gone, and so is the
 *   metadata (comments, location) a file can carry;
 * - the request stays small enough for the gateway to check in full.
 * The gateway still reads and checks this exact image before any model sees it.
 */
export const MAX_IMAGE_SIDE = 2048;

export function fitWithin(width: number, height: number, max = MAX_IMAGE_SIDE) {
  const scale = Math.min(1, max / Math.max(width, height));
  return {
    width: Math.max(1, Math.round(width * scale)),
    height: Math.max(1, Math.round(height * scale)),
  };
}

export async function prepareImage(file: File): Promise<string> {
  const bitmap = await createImageBitmap(file, { imageOrientation: "from-image" });
  try {
    const { width, height } = fitWithin(bitmap.width, bitmap.height);
    const canvas = document.createElement("canvas");
    canvas.width = width;
    canvas.height = height;
    const ctx = canvas.getContext("2d");
    if (!ctx) throw new Error("no canvas");
    ctx.fillStyle = "#ffffff";
    ctx.fillRect(0, 0, width, height);
    ctx.drawImage(bitmap, 0, 0, width, height);
    return canvas.toDataURL("image/jpeg", 0.9);
  } finally {
    bitmap.close();
  }
}

/** The redrawn picture as a file, so the server reads exactly what the model will get. */
export function dataUrlToFile(dataUrl: string, name: string): File {
  const [head, body = ""] = dataUrl.split(",", 2);
  const type = /data:([^;]+)/.exec(head ?? "")?.[1] ?? "image/jpeg";
  const bytes = Uint8Array.from(atob(body), (c) => c.charCodeAt(0));
  const base = name.replace(/\.[^.]+$/, "") || "image";
  return new File([bytes], `${base}.jpg`, { type });
}
