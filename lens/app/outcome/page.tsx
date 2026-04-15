export default function OutcomePage() {
  return (
    <main style={{ background: '#0d0d0d', color: '#d8d8d8', minHeight: '100vh', padding: 16, fontFamily: 'monospace' }}>
      <h1>AEGIS Lens — Live Outcome Monitor</h1>
      <div id="outcome-root" />
      <script
        dangerouslySetInnerHTML={{
          __html: `
(() => {
  const root = document.getElementById('outcome-root');
  if (!root) return;
  const render = (rows) => {
    const head = '<thead><tr><th>trace_id</th><th>agent</th><th>action_type</th><th>expected</th><th>actual</th><th>deviation</th><th>resolved</th></tr></thead>';
    const body = '<tbody>' + rows.map((r) => {
      const deviation = Number(r.deviation ?? 0);
      const color = deviation === 0 ? '#00ff9d' : (deviation < 0.3 ? '#f5a623' : '#ff4444');
      const failed = Number(r.resolved) === 2;
      const badge = failed ? '<span style="background:#ff4444;color:#111;padding:2px 6px;border-radius:4px;margin-left:6px">FAILED</span>' : '';
      return '<tr style="color:' + color + '"><td>' + (r.trace_id ?? '') + '</td><td>' + (r.agent ?? '') + '</td><td>' + (r.action_type ?? '') + '</td><td>' + JSON.stringify(r.expected ?? null) + '</td><td>' + JSON.stringify(r.actual ?? null) + '</td><td>' + deviation.toFixed(3) + '</td><td>' + (r.resolved ?? '') + badge + '</td></tr>';
    }).join('') + '</tbody>';
    root.innerHTML = '<table style="width:100%;border-collapse:collapse">' + head + body + '</table>';
  };

  const refresh = async () => {
    try {
      const rows = await fetch('/api/outcome').then((r) => r.json());
      render(Array.isArray(rows) ? rows.slice(0, 100) : []);
    } catch {
      render([]);
    }
  };

  refresh();
  setInterval(refresh, 5000);
})();`,
        }}
      />
    </main>
  );
}
