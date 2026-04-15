export default function StatusPage() {
  return (
    <main style={{ padding: 16, fontFamily: 'monospace' }}>
      <h1>Agent Status</h1>
      <div id="status-root" />
      <script dangerouslySetInnerHTML={{ __html: `
(() => {
  const root = document.getElementById('status-root');
  if (!root) return;
  const agents = ['warden','scribe','herald','forge','loop'];
  const seen = {};
  const color = (secs) => secs <= 60 ? 'green' : (secs <= 300 ? 'goldenrod' : 'red');
  const render = () => {
    const now = Date.now();
    root.innerHTML = '<ul>' + agents.map((a) => {
      const ts = seen[a] || 0;
      const age = ts ? Math.floor((now - ts) / 1000) : 999999;
      return '<li><span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:' + color(age) + ';margin-right:8px"></span>' + a + ' last seen ' + (ts ? age + 's ago' : 'never') + '</li>';
    }).join('') + '</ul>';
  };
  const refresh = async () => {
    try {
      const rows = await fetch('/api/events').then(() => []);
      void rows;
    } catch {}
    render();
  };
  const es = new EventSource('/api/events');
  es.onmessage = (evt) => {
    try { const e = JSON.parse(evt.data); if (e.agent) seen[e.agent] = Date.parse(e.ts || new Date().toISOString()); } catch {}
  };
  setInterval(refresh, 10000);
  render();
})();` }} />
    </main>
  );
}
