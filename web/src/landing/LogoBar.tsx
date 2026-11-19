import { useReducedMotion } from "motion/react";
import { InfiniteSlider } from "@/components/ui/infinite-slider";

/**
 * The AI tools Sentry works with, shown as logos (files in public/logos). Every tool is in the tool
 * catalogue (data/ai_tools.csv); ChatGPT, Claude and Gemini also have a live paste check in the
 * extension. Tools with no logo file yet (Microsoft Copilot, Otter.ai, Midjourney, Canva) are left out.
 */
export const SUPPORTED_TOOLS: { name: string; logo: string }[] = [
  { name: "ChatGPT", logo: "/logos/chatgpt.svg" },
  { name: "Claude", logo: "/logos/claude.svg" },
  { name: "Gemini", logo: "/logos/gemini.svg" },
  { name: "GitHub Copilot", logo: "/logos/github-copilot.svg" },
  { name: "Perplexity", logo: "/logos/perplexity.svg" },
  { name: "DeepSeek", logo: "/logos/deepseek.svg" },
  { name: "Grammarly", logo: "/logos/grammarly.svg" },
  { name: "DeepL", logo: "/logos/deepl.svg" },
];

/** A rolling strip under the hero. It stops moving for people who ask for reduced motion. */
export function LogoBar() {
  const reduced = useReducedMotion();
  const one = (copy: number) =>
    SUPPORTED_TOOLS.map((t) => (
      <span key={`${copy}-${t.name}`} className="logobar-item" aria-hidden={copy > 0 || undefined}>
        <img src={t.logo} alt={copy === 0 ? t.name : ""} className="logobar-img" />
      </span>
    ));
  // The slider shows its children twice and loops by half. Three sets per half keep the strip full
  // on any screen, so it never shows a gap, at the cost of a few repeated logos for a moment.
  const items = [...one(0), ...one(1), ...one(2)];
  return (
    <section className="logobar" aria-labelledby="logobar-title">
      <div className="logobar-band">
        <p id="logobar-title" className="logobar-title">
          Works with
        </p>
        {reduced ? (
          <div className="logobar-static">{one(0)}</div>
        ) : (
          <InfiniteSlider gap={40} duration={70} className="logobar-track">
            {items}
          </InfiniteSlider>
        )}
      </div>
    </section>
  );
}
