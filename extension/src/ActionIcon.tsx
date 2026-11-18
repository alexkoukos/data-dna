import { Ban, Check, EyeOff, House, TriangleAlert } from "lucide-react";

const ICONS = { allow: Check, mask: EyeOff, warn: TriangleAlert, local: House, block: Ban };

/** The outcome icon (lucide), always shown beside the outcome word. */
export function ActionIcon({ action, size = 12 }: { action: string; size?: number }) {
  const Icon = ICONS[action as keyof typeof ICONS];
  return Icon ? <Icon aria-hidden="true" size={size} strokeWidth={2.5} /> : null;
}
