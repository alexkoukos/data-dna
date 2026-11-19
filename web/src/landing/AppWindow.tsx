import type { ReactNode } from "react";
import { Scaled } from "./Scaled";

// The demo sits in a clean app window not on a laptop picture.
// The window is drawn at 720 x 450 and scaled up to the width it is given.
export function AppWindow({ children }: { children: ReactNode }) {
  return (
    <div className="appwin">
      <Scaled width={720} height={450} max={2.2} className="appwin-scaled">
        {children}
      </Scaled>
    </div>
  );
}
