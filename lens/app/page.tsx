const cards = [
  'Trace Viewer',
  'Action-Consequence Map',
  'Wealth Dashboard',
  'Memory Browser',
  'Agent Status',
];

export default function Page() {
  return (
    <main>
      <h1>AEGIS Lens</h1>
      <p>Read-only v1 dashboard with unified trace spine.</p>
      <ul>
        {cards.map((c) => (
          <li key={c}>{c}</li>
        ))}
      </ul>
    </main>
  );
}
