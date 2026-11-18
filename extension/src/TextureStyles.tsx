import { TEXTURE_CSS } from "./texture";

/** Render once at the root of every extension page: the texture button styles. */
export function TextureStyles() {
  return <style>{TEXTURE_CSS}</style>;
}
