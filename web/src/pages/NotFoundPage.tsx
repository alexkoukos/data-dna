import { Link } from "react-router-dom";

/** Any address the app does not know. Says so, and offers the way back. */
export default function NotFoundPage() {
  return (
    <main className="mx-auto max-w-3xl px-4 py-16 text-center">
      <p className="eyebrow">Pyli</p>
      <h1 className="text-2xl font-semibold text-ink-900">This page does not exist</h1>
      <p className="mt-2 text-ink-600">
        The address may be mistyped or from an older version. Start again from the home page.
      </p>
      <Link
        to="/app"
        className="mt-6 inline-flex min-h-11 items-center rounded-md bg-brand-600 px-4 font-medium text-white hover:bg-brand-700"
      >
        Go to the home page
      </Link>
    </main>
  );
}
