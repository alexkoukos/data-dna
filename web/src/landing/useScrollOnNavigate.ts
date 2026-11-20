import { useEffect } from "react";
import { useLocation } from "react-router-dom";

/**
 * A client-side link keeps the old scroll position, so a footer link lands at the bottom of the
 * new page and looks like it did nothing. Go to the top on every new page, or to the #section
 * when the link names one (lazy pages render it a moment later, so look for it for up to 2 s).
 */
export function useScrollOnNavigate() {
  const { pathname, hash } = useLocation();
  useEffect(() => {
    if (!hash) {
      window.scrollTo(0, 0);
      return;
    }
    const id = decodeURIComponent(hash.slice(1));
    let tries = 0;
    let timer = 0;
    const find = () => {
      const el = document.getElementById(id);
      if (el) el.scrollIntoView();
      else if (tries++ < 20) timer = window.setTimeout(find, 100);
    };
    find();
    return () => window.clearTimeout(timer);
  }, [pathname, hash]);
}
