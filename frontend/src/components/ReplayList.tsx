import type { ReplaySummary } from "../types";
import { formatDuration } from "../utils";

interface ReplayListProps {
  replays: ReplaySummary[];
  selectedId?: string;
  onSelect: (replay: ReplaySummary) => void;
}

export function ReplayList({ replays, selectedId, onSelect }: ReplayListProps) {
  return (
    <section className="replay-list" aria-labelledby="recent-replays-title">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Current session</p>
          <h2 id="recent-replays-title">Recent replays</h2>
        </div>
        <span className="count-badge">{replays.length}</span>
      </div>
      {replays.length === 0 ? (
        <p className="empty-state">Replays you analyze will appear here until the API restarts.</p>
      ) : (
        <div className="replay-items">
          {replays.map((replay) => (
            <button
              className={`replay-item ${selectedId === replay.replay_id ? "is-selected" : ""}`}
              key={replay.replay_id}
              type="button"
              onClick={() => onSelect(replay)}
            >
              <span>
                <strong>{replay.players.map((player) => player.name).join(" vs ")}</strong>
                <small>{replay.map_name}</small>
              </span>
              <span className="replay-item-meta">
                {formatDuration(replay.duration_seconds)}
                <small>{replay.filename}</small>
              </span>
            </button>
          ))}
        </div>
      )}
    </section>
  );
}
