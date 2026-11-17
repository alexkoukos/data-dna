import type { ReactNode } from "react";
import { LaptopArt, HOLE } from "./LaptopArt";
import { Scaled } from "./Scaled";

// The hero screen sits behind a vector laptop (LaptopArt) whose display is a real hole.
export const LAPTOP_W = 812;
export const LAPTOP_H = 480;
// The browser window is 720 x 450; a 26 px menu bar above it makes 720 x 476, the hole's ratio.
const CONTENT = { w: 720, h: 476 };
const FIT = HOLE.w / CONTENT.w;

export function Laptop({ children }: { children: ReactNode }) {
  return (
    <Scaled width={LAPTOP_W} height={LAPTOP_H} className="laptop-wrap">
      <div className="laptop">
        <div className="laptop-glow" aria-hidden="true" />
        <div className="laptop-contact" aria-hidden="true" />
        <LaptopArt className="laptop-reflection" />
        <div
          className="laptop-hole"
          style={{ left: HOLE.x, top: HOLE.y, width: HOLE.w, height: HOLE.h }}
        >
          <div
            className="laptop-content"
            style={{ width: CONTENT.w, height: CONTENT.h, transform: `scale(${FIT})` }}
          >
            <div className="menubar" aria-hidden="true">
              <span className="menubar-app">Browser</span>
              <span>File</span>
              <span>Edit</span>
              <span>View</span>
              <span>History</span>
              <span className="menubar-status">
                <svg
                  width="16"
                  height="12"
                  viewBox="0 0 16 12"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                >
                  <path d="M1.5 4.2a9 9 0 0 1 13 0M3.8 6.8a5.7 5.7 0 0 1 8.4 0M6.2 9.3a2.4 2.4 0 0 1 3.6 0" />
                </svg>
                <svg width="26" height="12" viewBox="0 0 26 12" fill="none">
                  <rect
                    x="0.75"
                    y="1.25"
                    width="21"
                    height="9.5"
                    rx="2.5"
                    stroke="currentColor"
                    strokeWidth="1.2"
                  />
                  <rect x="2.5" y="3" width="14" height="6" rx="1.2" fill="currentColor" />
                  <path
                    d="M23.6 4.4v3.2"
                    stroke="currentColor"
                    strokeWidth="1.6"
                    strokeLinecap="round"
                  />
                </svg>
                <span>Tue 17 Nov 14:32</span>
              </span>
            </div>
            <div className="laptop-screen">{children}</div>
            <div className="glass" aria-hidden="true" />
          </div>
        </div>
        <div className="laptop-spill" aria-hidden="true" />
        <LaptopArt className="laptop-frame" />
      </div>
    </Scaled>
  );
}
