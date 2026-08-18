import { useEffect, useMemo, useRef } from "react";

import type { FrameSnapshot } from "../types";

interface MinimapProps {
  frame: FrameSnapshot;
  samples: FrameSnapshot[];
}

interface Bounds {
  minX: number;
  maxX: number;
  minY: number;
  maxY: number;
}

const PLAYER_COLORS = ["#22d3ee", "#fb4d4d", "#f5c451", "#a78bfa"];

export function Minimap({ frame, samples }: MinimapProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const bounds = useMemo(() => calculateBounds(samples), [samples]);

  useEffect(() => {
    const canvas = canvasRef.current;
    const context = canvas?.getContext("2d");
    if (!canvas || !context) return;

    const size = canvas.width;
    context.clearRect(0, 0, size, size);
    drawMap(context, size);
    frame.players.forEach((player, playerIndex) => {
      context.fillStyle = PLAYER_COLORS[playerIndex % PLAYER_COLORS.length];
      player.units.forEach((unit) => {
        if (!unit.position) return;
        const point = project(unit.position.x, unit.position.y, bounds, size);
        context.globalAlpha = unit.completed ? 0.92 : 0.5;
        context.beginPath();
        context.arc(point.x, point.y, unit.completed ? 2.8 : 2, 0, Math.PI * 2);
        context.fill();
      });
    });
    context.globalAlpha = 1;
  }, [bounds, frame]);

  return (
    <div className="minimap-wrap">
      <canvas ref={canvasRef} className="minimap" width={600} height={600} />
      <div className="minimap-legend">
        {frame.players.map((player, index) => (
          <span key={player.player_id}>
            <i style={{ background: PLAYER_COLORS[index % PLAYER_COLORS.length] }} /> Player {index + 1}
          </span>
        ))}
      </div>
    </div>
  );
}

function calculateBounds(samples: FrameSnapshot[]): Bounds {
  const positions = samples.flatMap((sample) =>
    sample.players.flatMap((player) =>
      player.units.flatMap((unit) => (unit.position ? [unit.position] : [])),
    ),
  );
  if (positions.length === 0) return { minX: 0, maxX: 256, minY: 0, maxY: 256 };
  return {
    minX: Math.min(...positions.map((position) => position.x)),
    maxX: Math.max(...positions.map((position) => position.x)),
    minY: Math.min(...positions.map((position) => position.y)),
    maxY: Math.max(...positions.map((position) => position.y)),
  };
}

function project(x: number, y: number, bounds: Bounds, size: number) {
  const padding = 20;
  const width = Math.max(bounds.maxX - bounds.minX, 1);
  const height = Math.max(bounds.maxY - bounds.minY, 1);
  return {
    x: padding + ((x - bounds.minX) / width) * (size - padding * 2),
    y: size - padding - ((y - bounds.minY) / height) * (size - padding * 2),
  };
}

function drawMap(context: CanvasRenderingContext2D, size: number) {
  const gradient = context.createLinearGradient(0, 0, size, size);
  gradient.addColorStop(0, "#111a28");
  gradient.addColorStop(1, "#070b12");
  context.fillStyle = gradient;
  context.fillRect(0, 0, size, size);
  context.strokeStyle = "rgba(114, 151, 180, 0.12)";
  context.lineWidth = 1;
  for (let position = 0; position <= size; position += size / 8) {
    context.beginPath();
    context.moveTo(position, 0);
    context.lineTo(position, size);
    context.stroke();
    context.beginPath();
    context.moveTo(0, position);
    context.lineTo(size, position);
    context.stroke();
  }
}
