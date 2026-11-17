import type { ReactNode } from "react";
import { Scaled } from "./Scaled";

// The hero screen sits behind a laptop photo whose display is transparent. Numbers are in the
// photo's own pixels (812 x 480): the display hole is x 106..684, y 30..412, with a notch on top.
export const LAPTOP_W = 812;
export const LAPTOP_H = 480;
const HOLE = { x: 106, y: 30, w: 579, h: 383 };
// The browser window is 720 x 450; a 26 px menu bar above it makes 720 x 476, the hole's ratio.
const CONTENT = { w: 720, h: 476 };
const FIT = HOLE.w / CONTENT.w;

export function Laptop({ children }: { children: ReactNode }) {
  return (
    <Scaled width={LAPTOP_W} height={LAPTOP_H} className="laptop-wrap">
      <div className="laptop">
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
              <span className="menubar-clock">Tue 17 Nov 14:32</span>
            </div>
            <div className="laptop-screen">{children}</div>
          </div>
        </div>
        <img
          className="laptop-frame"
          src="/brand/macbook-frame.png"
          alt=""
          width={LAPTOP_W}
          height={LAPTOP_H}
        />
      </div>
    </Scaled>
  );
}
