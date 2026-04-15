export default function WealthPage() {
  return (
    <main style={{ padding: 16, fontFamily: 'monospace' }}>
      <h1>Wealth Dashboard</h1>
      <noscript><p>Static mode enabled.</p></noscript>
      <div id="wealth-root">Loading...</div>
      <script dangerouslySetInnerHTML={{ __html: `
(() => {
  const node = document.getElementById('wealth-root');
  if (!node) return;
  const totals = { projected: 0, realized: 0, tokens: 0, dollars: 0 };
  const render = () => {
    const clampedProjected = Math.max(0, totals.projected);
    const clampedRealized = Math.max(0, totals.realized);
    const warn = totals.projected < 0 || totals.realized < 0 ? '<span style="color:#d97706">warning: clamped negative wealth</span>' : '';
    node.innerHTML = '<p>projected_wealth=' + clampedProjected.toFixed(2) + '</p><p>realized_wealth=' + clampedRealized.toFixed(2) + '</p><p>total_cost_tokens=' + totals.tokens + '</p><p>total_cost_dollars=' + totals.dollars.toFixed(4) + '</p>' + warn;
  };
  const es = new EventSource('/api/events');
  es.onmessage = (evt) => {
    try {
      const e = JSON.parse(evt.data);
      const wt = e.wealth_impact && e.wealth_impact.type;
      const val = Number((e.wealth_impact && e.wealth_impact.value) || 0);
      if (wt === 'projected') totals.projected += val;
      if (wt === 'realized') totals.realized += val;
      totals.tokens += Number((e.cost && e.cost.tokens) || 0);
      totals.dollars += Number((e.cost && e.cost.dollars) || 0);
      render();
    } catch {}
  };
  render();
})();` }} />
    </main>
  );
}
