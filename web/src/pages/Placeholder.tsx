import { Thyro } from "../components/Thyro";

export function Placeholder({ title, note }: { title: string; note: string }) {
  return (
    <main className="mx-auto flex max-w-3xl flex-col items-center p-8 text-center">
      <Thyro pose="master" size={360} />
      <h1 className="mt-4 text-4xl font-semibold text-ink-900">{title}</h1>
      <p className="mt-2 text-ink-600">{note}</p>
    </main>
  );
}
