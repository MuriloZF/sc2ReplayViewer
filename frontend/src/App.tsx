function App() {
  return (
    <main className="app-shell">
      <section className="hero">
        <p className="eyebrow">Replay intelligence</p>
        <h1>SC2 Replay Viewer</h1>
        <p className="subtitle">
          Upload a StarCraft II replay to inspect its timeline, economy, army, and build order.
        </p>
        <button type="button" disabled>
          Replay upload coming next
        </button>
      </section>
      <section className="preview-grid" aria-label="Planned replay analysis">
        <article>
          <span>01</span>
          <h2>Timeline</h2>
          <p>Compare resources, workers, supply, and army strength over game time.</p>
        </article>
        <article>
          <span>02</span>
          <h2>Minimap</h2>
          <p>Replay reconstructed unit positions on an animated battlefield.</p>
        </article>
        <article>
          <span>03</span>
          <h2>Build order</h2>
          <p>Review structures, upgrades, and unit production in sequence.</p>
        </article>
      </section>
    </main>
  );
}

export default App;
