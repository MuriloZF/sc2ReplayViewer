import { useMemo } from "react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { FrameSnapshot, Player } from "../types";
import { formatDuration } from "../utils";

interface ResourceChartProps {
  samples: FrameSnapshot[];
  players: Player[];
}

const COLORS = ["#22d3ee", "#fb4d4d"];

export function ResourceChart({ samples, players }: ResourceChartProps) {
  const data = useMemo(
    () =>
      samples.map((frame) => {
        const row: Record<string, number> = { time: frame.game_time_seconds };
        frame.players.forEach((player) => {
          row[`army-${player.player_id}`] = player.army_supply;
          row[`workers-${player.player_id}`] = player.workers;
        });
        return row;
      }),
    [samples],
  );

  return (
    <section className="panel chart-panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Composition over time</p>
          <h3>Army and workers</h3>
        </div>
      </div>
      <div className="chart-area">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 8, right: 12, bottom: 0, left: -16 }}>
            <CartesianGrid stroke="#1b2939" strokeDasharray="3 5" vertical={false} />
            <XAxis
              dataKey="time"
              tickFormatter={formatDuration}
              stroke="#64748b"
              tick={{ fontSize: 11 }}
            />
            <YAxis stroke="#64748b" tick={{ fontSize: 11 }} />
            <Tooltip
              labelFormatter={(value) => formatDuration(Number(value))}
              contentStyle={{ background: "#0c1420", border: "1px solid #26364b" }}
            />
            <Legend />
            {players.slice(0, 2).flatMap((player, index) => [
              <Line
                key={`army-${player.player_id}`}
                dataKey={`army-${player.player_id}`}
                name={`${player.name} army`}
                stroke={COLORS[index]}
                dot={false}
                strokeWidth={2}
              />,
              <Line
                key={`workers-${player.player_id}`}
                dataKey={`workers-${player.player_id}`}
                name={`${player.name} workers`}
                stroke={COLORS[index]}
                strokeDasharray="5 5"
                dot={false}
              />,
            ])}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}
