import { useEffect, useMemo, useState } from "react";

import { getBuildOrder, getMapMetadata, getMinimapUrl, getTimeline } from "../api";
import type {
  BuildOrderEntry,
  FrameSnapshot,
  MapBounds,
  Player,
  PlayerSnapshot,
  ReplaySummary,
} from "../types";
import { formatDuration, formatNumber } from "../utils";
import { BuildOrders } from "./BuildOrders";
import { Minimap } from "./Minimap";
import { RaceIcon } from "./RaceIcon";
import { ResourceChart } from "./ResourceChart";
import { WinProbability } from "./WinProbability";

interface AnalysisDashboardProps {
  replay: ReplaySummary;
}

export function AnalysisDashboard({ replay }: AnalysisDashboardProps) {
  const [samples, setSamples] = useState<FrameSnapshot[]>([]);
  const [buildOrder, setBuildOrder] = useState<BuildOrderEntry[]>([]);
  const [mapBounds, setMapBounds] = useState<MapBounds | null>(null);
  const [frameIndex, setFrameIndex] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    Promise.all([
      getTimeline(replay.replay_id),
      getBuildOrder(replay.replay_id),
      getMapMetadata(replay.replay_id).catch(() => null),
    ])
      .then(([timeline, order, mapMetadata]) => {
        if (!active) return;
        setSamples(timeline.samples);
        setBuildOrder(order.entries);
        setMapBounds(mapMetadata?.bounds ?? null);
      })
      .catch((reason: unknown) => {
        if (active) setError(reason instanceof Error ? reason.message : "Unable to load analysis");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [replay.replay_id]);

  useEffect(() => {
    if (!playing || samples.length < 2) return;
    const timer = window.setInterval(() => {
      setFrameIndex((current) => {
        if (current >= samples.length - 1) {
          setPlaying(false);
          return current;
        }
        return current + 1;
      });
    }, 450);
    return () => window.clearInterval(timer);
  }, [playing, samples.length]);

  const frame = samples[frameIndex];
  const playerSnapshots = useMemo(
    () =>
      replay.players.map(
        (player) => frame?.players.find((item) => item.player_id === player.player_id) ?? emptyPlayer(player),
      ),
    [frame, replay.players],
  );

  if (loading) return <DashboardSkeleton replay={replay} />;
  if (error) return <div className="notice error-notice">{error}</div>;
  if (!frame) return <div className="notice">This replay did not produce timeline samples.</div>;

  return (
    <div className="dashboard">
      <MatchHeader replay={replay} currentTime={frame.game_time_seconds} />
      <div className="playback-bar panel">
        <button
          className="play-button"
          type="button"
          onClick={() => {
            if (frameIndex === samples.length - 1) setFrameIndex(0);
            setPlaying((value) => !value);
          }}
          aria-label={playing ? "Pause timeline" : "Play timeline"}
        >
          {playing ? "Ⅱ" : "▶"}
        </button>
        <span className="mono">{formatDuration(frame.game_time_seconds)}</span>
        <input
          aria-label="Replay timeline"
          type="range"
          min="0"
          max={samples.length - 1}
          value={frameIndex}
          onChange={(event) => {
            setPlaying(false);
            setFrameIndex(Number(event.target.value));
          }}
        />
        <span className="mono muted">{formatDuration(replay.duration_seconds)}</span>
      </div>
      <div className="dashboard-grid">
        <WinProbability replayId={replay.replay_id} players={replay.players} gameLoop={frame.game_loop} />
        <section className="panel minimap-panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">{replay.map_name}</p>
              <h3>Minimap</h3>
            </div>
            <span className="count-badge">
              {playerSnapshots.reduce((total, player) => total + player.units.length, 0)} units
            </span>
          </div>
          <Minimap
            frame={frame}
            samples={samples}
            imageUrl={getMinimapUrl(replay.replay_id)}
            mapBounds={mapBounds}
          />
        </section>
        <BuildOrders entries={buildOrder} players={replay.players} currentTime={frame.game_time_seconds} />
      </div>
      <div className="metric-cards">
        {replay.players.slice(0, 2).map((player, index) => (
          <PlayerMetrics
            key={player.player_id}
            player={player}
            snapshot={playerSnapshots[index]}
            index={index}
          />
        ))}
      </div>
      <ResourceChart samples={samples} players={replay.players} />
    </div>
  );
}

function MatchHeader({ replay, currentTime }: { replay: ReplaySummary; currentTime: number }) {
  const [playerOne, playerTwo] = replay.players;
  return (
    <header className="match-header panel">
      {playerOne && <MatchPlayer player={playerOne} index={0} />}
      <div className="match-center">
        <span className="time-badge">GAME TIME · {formatDuration(currentTime)}</span>
        <small>{replay.map_name}</small>
      </div>
      {playerTwo && <MatchPlayer player={playerTwo} index={1} />}
    </header>
  );
}

function MatchPlayer({ player, index }: { player: Player; index: number }) {
  return (
    <div className={`match-player player-${index + 1}`}>
      <span className="race-mark">
        <RaceIcon race={player.race} />
      </span>
      <span>
        <strong>{player.name}</strong>
        <small>{player.race}</small>
      </span>
    </div>
  );
}

function PlayerMetrics({
  player,
  snapshot,
  index,
}: {
  player: Player;
  snapshot: PlayerSnapshot;
  index: number;
}) {
  const metrics = [
    ["Minerals", snapshot.minerals],
    ["Gas", snapshot.vespene],
    ["Supply", `${formatNumber(snapshot.supply_used)}/${formatNumber(snapshot.supply_cap)}`],
    ["Army", formatNumber(snapshot.army_supply)],
    ["Workers", snapshot.workers],
  ];
  return (
    <section className={`panel metric-card player-${index + 1}`}>
      <div className="metric-card-header">
        <strong>{player.name}</strong>
        <span>{player.race}</span>
      </div>
      <dl>
        {metrics.map(([label, value]) => (
          <div key={label}>
            <dt>{label}</dt>
            <dd>{value}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

function DashboardSkeleton({ replay }: { replay: ReplaySummary }) {
  return (
    <div className="dashboard-loading panel" role="status">
      <span className="loading-orbit" />
      <div>
        <strong>Loading {replay.map_name}</strong>
        <p>Loading replay data…</p>
      </div>
    </div>
  );
}

function emptyPlayer(player: Player): PlayerSnapshot {
  return {
    player_id: player.player_id,
    minerals: 0,
    vespene: 0,
    supply_used: 0,
    supply_cap: 0,
    army_supply: 0,
    workers: 0,
    units: [],
  };
}
