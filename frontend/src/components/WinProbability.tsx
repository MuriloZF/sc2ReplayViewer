import { useEffect, useState } from "react";

import { getWinProbability } from "../api";
import type { Player, WinProbabilityResponse } from "../types";

interface WinProbabilityProps {
  replayId: string;
  players: Player[];
  gameLoop: number;
}

export function WinProbability({ replayId, players, gameLoop }: WinProbabilityProps) {
  const [result, setResult] = useState<{
    replayId: string;
    data?: WinProbabilityResponse;
    error?: string;
  } | null>(null);

  useEffect(() => {
    let active = true;
    getWinProbability(replayId)
      .then((data) => {
        if (active) setResult({ replayId, data });
      })
      .catch((reason: unknown) => {
        if (active) {
          setResult({
            replayId,
            error: reason instanceof Error ? reason.message : "Unable to load win probabilities.",
          });
        }
      });
    return () => {
      active = false;
    };
  }, [replayId]);

  const current = result?.replayId === replayId ? result : null;
  const sample = current?.data?.samples.find((item) => item.game_loop === gameLoop);
  const displayedPlayers = players.slice(0, 2).map((player) => ({
    ...player,
    probability: sample?.players.find((item) => item.player_id === player.player_id)?.win_probability,
  }));
  const available =
    players.length === 2 &&
    displayedPlayers.every((player) => player.probability !== undefined);
  // Derive both displayed percentages from one rounded value so they sum to 100%.
  const firstPercent = Math.round((displayedPlayers[0]?.probability ?? 0) * 100);

  return (
    <section className="panel probability-panel" aria-label="Win probability">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">{current?.data?.model_name ?? "Model estimate"}</p>
          <h3>Win probability</h3>
        </div>
      </div>
      {available ? (
        <>
          <div className="probability-display">
            <div className="probability-stack" aria-hidden="true">
              {displayedPlayers.map((player, index) => (
                <div
                  className={`probability-segment player-${index + 1}`}
                  style={{ height: `${(player.probability ?? 0) * 100}%` }}
                  key={player.player_id}
                />
              ))}
            </div>
            <div className="probability-values">
              {displayedPlayers.map((player, index) => (
                <div className={`player-${index + 1}`} key={player.player_id}>
                  <span>{player.name}</span>
                  <strong>{index === 0 ? firstPercent : 100 - firstPercent}%</strong>
                </div>
              ))}
            </div>
          </div>
          <p className="probability-caption">Estimated from the current game state.</p>
        </>
      ) : (
        <div className="probability-pending" role="status">
          <strong>{current?.error ? "Unavailable" : current ? "Waiting for data" : "Loading…"}</strong>
          <span>
            {current?.error ??
              (current
                ? "No initialized economy data at this point in the replay."
                : "Calculating win probabilities…")}
          </span>
        </div>
      )}
    </section>
  );
}
