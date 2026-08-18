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
          const visibleEntries = entries
            .filter(
              (entry) => entry.player_id === player.player_id && entry.game_time_seconds <= currentTime,
            )
            .slice(-14);
          return (
            <div className={`build-column player-${playerIndex + 1}`} key={player.player_id}>
              <h4>{player.name}</h4>
              {visibleEntries.length === 0 ? (
                <p className="empty-state compact">No production events yet.</p>
              ) : (
                <ol>
                  {visibleEntries.map((entry, index) => (
                    <li key={`${entry.game_loop}-${entry.item_name}-${index}`}>
                      <time>{formatDuration(entry.game_time_seconds)}</time>
                      <i />
                      <span>{entry.item_name}</span>
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
