import type { BuildOrderEntry, Player } from "../types";
import { formatDuration } from "../utils";

interface BuildOrdersProps {
  entries: BuildOrderEntry[];
  players: Player[];
  currentTime: number;
}

export function BuildOrders({ entries, players, currentTime }: BuildOrdersProps) {
  return (
    <section className="panel build-panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Production log</p>
          <h3>Build order progression</h3>
        </div>
      </div>
      <div className="build-columns">
        {players.slice(0, 2).map((player, playerIndex) => {
          const playerEntries = entries.filter((entry) => entry.player_id === player.player_id);
          return (
            <div className={`build-column player-${playerIndex + 1}`} key={player.player_id}>
              <div className="build-column-heading">
                <h4>{player.name}</h4>
                <span>{playerEntries.length} events</span>
              </div>
              {playerEntries.length === 0 ? (
                <p className="empty-state compact">No build-order events were found.</p>
              ) : (
                <ol>
                  {playerEntries.map((entry, index) => (
                    <li
                      className={entry.game_time_seconds > currentTime ? "is-future" : ""}
                      key={`${entry.game_loop}-${entry.item_name}-${index}`}
                    >
                      <time>{formatDuration(entry.game_time_seconds)}</time>
                      <i />
                      <span className="build-item">
                        <strong>{entry.item_name}</strong>
                        <small>{entry.category}</small>
                      </span>
                      <span className="supply-badge">
                        {entry.supply === null ? "—" : Math.round(entry.supply)}
                      </span>
                    </li>
                  ))}
                </ol>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}
