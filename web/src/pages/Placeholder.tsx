export function Placeholder({ title, note }: { title: string; note: string }) {
  return (
    <main className="mx-auto max-w-3xl p-8">
      <h1 className="text-2xl font-semibold">{title}</h1>
      <p className="mt-2 text-ink-600">{note}</p>
    </main>
  );
}
