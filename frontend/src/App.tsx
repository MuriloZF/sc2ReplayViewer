import { lazy, Suspense, useEffect, useState } from "react";

import { listReplays, uploadReplay } from "./api";
import { ReplayList } from "./components/ReplayList";
import { UploadPanel } from "./components/UploadPanel";
import type { ReplaySummary } from "./types";

type View = "upload" | "dashboard";

const AnalysisDashboard = lazy(() =>
  import("./components/AnalysisDashboard").then((module) => ({
    default: module.AnalysisDashboard,
  })),
);

function App() {
  const [replays, setReplays] = useState<ReplaySummary[]>([]);
  const [selected, setSelected] = useState<ReplaySummary | null>(null);
  const [view, setView] = useState<View>("upload");
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listReplays()
      .then(setReplays)
      .catch((reason: unknown) => {
        setError(reason instanceof Error ? reason.message : "Unable to reach the replay API");
      });
  }, []);

  async function analyze(file: File) {
    setUploading(true);
    setError(null);
    try {
      const replay = await uploadReplay(file);
      setReplays((current) => [replay, ...current.filter((item) => item.replay_id !== replay.replay_id)]);
      setSelected(replay);
      setView("dashboard");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Replay analysis failed");
    } finally {
      setUploading(false);
    }
  }

  function openReplay(replay: ReplaySummary) {
    setSelected(replay);
    setView("dashboard");
    setError(null);
  }

  return (
    <div className="application">
      <nav className="navbar">
        <button className="brand" type="button" onClick={() => setView("upload")}>
          <span className="brand-mark">Ⅱ</span>
          <span>
            SC2 <em>REPLAY ROOM</em>
          </span>
        </button>
        <div className="nav-links" aria-label="Primary navigation">
          <button
            className={view === "upload" ? "is-active" : ""}
            type="button"
            onClick={() => setView("upload")}
          >
            Replays
          </button>
          <button
            className={view === "dashboard" ? "is-active" : ""}
            type="button"
            disabled={!selected}
            onClick={() => setView("dashboard")}
          >
            Analysis
          </button>
        </div>
      </nav>

      <main className="app-shell">
        {error && (
          <div className="notice error-notice" role="alert">
            <span>{error}</span>
            <button type="button" onClick={() => setError(null)} aria-label="Dismiss error">
              ×
            </button>
          </div>
        )}

        {view === "upload" ? (
          <div className="landing-layout">
            <UploadPanel busy={uploading} onUpload={analyze} />
            <ReplayList replays={replays} selectedId={selected?.replay_id} onSelect={openReplay} />
          </div>
        ) : selected ? (
          <Suspense fallback={<div className="dashboard-loading panel">Loading dashboard…</div>}>
            <AnalysisDashboard key={selected.replay_id} replay={selected} />
          </Suspense>
        ) : null}
      </main>
    </div>
  );
}

export default App;
