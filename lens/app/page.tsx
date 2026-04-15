import Link from 'next/link';

export default function Page() {
  return (
    <main style={{ background: '#0d0d0d', color: '#d8d8d8', minHeight: '100vh', padding: 16, fontFamily: 'monospace' }}>
      <h1>AEGIS Lens — Live Trace Viewer</h1>
      <nav style={{ display: 'flex', gap: 12, marginBottom: 16 }}>
        <Link href="/wealth">wealth</Link>
        <Link href="/memory">memory</Link>
        <Link href="/status">status</Link>
      </nav>
      <noscript>
        <p>JavaScript is disabled. Live updates are unavailable, but static navigation works.</p>
      </noscript>
      <div id="trace-root" />
      <script
        dangerouslySetInnerHTML={{
          __html: `
(() => {
  const root = document.getElementById('trace-root');
  if (!root) return;
  root.innerHTML = '<table style="width:100%;border-collapse:collapse"><thead><tr><th>time</th><th>agent</th><th>event_type</th><th>policy_state</th><th>consequence_summary</th><th>wealth_impact</th></tr></thead><tbody id="trace-body"></tbody></table>';
  const body = document.getElementById('trace-body');
  if (!body) return;
  const rows = [];
  const es = new EventSource('/api/events');
  es.onmessage = (evt) => {
    try {
      const e = JSON.parse(evt.data);
      rows.push(e);
      while (rows.length > 200) rows.shift();
      body.innerHTML = rows.map((r) => {
        const approved = (r.policy_state || '') === 'approved';
        const style = approved ? 'color:#00ff9d' : '';
        return '<tr style="' + style + '"><td>' + (r.ts || '') + '</td><td>' + (r.agent || '') + '</td><td>' + (r.event_type || '') + '</td><td>' + (r.policy_state || '') + '</td><td>' + (r.consequence_summary || '') + '</td><td>' + ((r.wealth_impact && r.wealth_impact.value) || 0) + '</td></tr>';
      }).join('');
      window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' });
    } catch {}
  };
})();`,
        }}
      />
    </main>
  );
}
