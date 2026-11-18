import { Bee } from "../components/Bee";
export function Placeholder({ title, note }: { title: string; note: string }) {
  return (
    <main className="mx-auto flex max-w-3xl flex-col items-center p-8 text-center">
      <Bee size={144} />
      <h1 className="mt-4 text-4xl font-semibold text-ink-900">{title}</h1>
      <p className="mt-2 text-ink-600">{note}</p>
    </main>
  );
}
