import { Link, useLocation } from "react-router-dom";
import { TextureButton } from "@/components/ui/texture-button";
import { Sentinel } from "@/components/Sentinel";
import "./landing.css";

/** Shown for any address that is not a page. It looks like a scan result: nothing found. */
export default function NotFound() {
  const { pathname } = useLocation();
  return (
    <main id="main" className="nf">
      <div className="nf-in">
        <Sentinel size={64} className="nf-mark" />
        <p className="nf-code">404</p>
        <h1>Nothing here.</h1>
        <p className="lead">This address is not a page, or it moved.</p>
        <div className="nf-scan" role="status">
          <span>Scanned</span>
          <code>{pathname.length > 60 ? `${pathname.slice(0, 60)}…` : pathname}</code>
          <b>0 pages found</b>
        </div>
        <div className="cta-row">
          <TextureButton asChild variant="primary" size="lg">
            <Link to="/">Back to the start</Link>
          </TextureButton>
          <TextureButton asChild variant="secondary" size="lg">
            <Link to="/how-it-works">How it works</Link>
          </TextureButton>
        </div>
      </div>
    </main>
  );
}
