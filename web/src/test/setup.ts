import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

// Vitest globals are off, so Testing Library does not clean up the DOM by itself.
afterEach(() => cleanup());

// jsdom has no ResizeObserver, which the chat container needs to keep the newest message in view.
globalThis.ResizeObserver ??= class {
  observe() {}
  unobserve() {}
  disconnect() {}
};
