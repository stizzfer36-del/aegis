export default function MemoryPage() {
  return (
    <main style={{ padding: 16, fontFamily: 'monospace' }}>
      <h1>Memory Browser</h1>
      <noscript><p>Enable JavaScript for pagination controls.</p></noscript>
      <div id="memory-root" />
      <script dangerouslySetInnerHTML={{ __html: `
(() => {
  const root = document.getElementById('memory-root');
  if (!root) return;
  let page = 1;
  let topic = '';
  const render = async () => {
    const data = await fetch('/api/memory?page=' + page + '&topic=' + encodeURIComponent(topic)).then((r) => r.json());
    const rows = data.rows || [];
    root.innerHTML = '<input id="topic-filter" placeholder="topic filter" value="' + topic + '"/><button id="apply">apply</button>' +
      '<table><thead><tr><th>trace_id</th><th>topic</th><th>content</th></tr></thead><tbody>' +
      rows.map((r) => '<tr><td>' + (r.trace_id || '') + '</td><td>' + (r.topic || '') + '</td><td>' + String(r.content || '').slice(0, 120) + '</td></tr>').join('') +
      '</tbody></table>' +
      '<button id="prev" ' + (page <= 1 ? 'disabled' : '') + '>prev</button><button id="next" ' + (page * 50 >= (data.total || 0) ? 'disabled' : '') + '>next</button>';
    document.getElementById('apply')?.addEventListener('click', () => {
      topic = (document.getElementById('topic-filter') as HTMLInputElement)?.value || '';
      page = 1;
      void render();
    });
    document.getElementById('prev')?.addEventListener('click', () => { page = Math.max(1, page - 1); void render(); });
    document.getElementById('next')?.addEventListener('click', () => { page += 1; void render(); });
  };
  void render();
})();` }} />
    </main>
  );
}
