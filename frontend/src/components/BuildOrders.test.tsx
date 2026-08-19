import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { BuildOrderEntry, Player } from "../types";
import { BuildOrders } from "./BuildOrders";

const players: Player[] = [
  { player_id: 1, name: "Alpha", race: "Terran", result: "win", win_probability: null },
  { player_id: 2, name: "Bravo", race: "Zerg", result: "loss", win_probability: null },
];

const entries: BuildOrderEntry[] = [
  {
    player_id: 1,
    game_loop: 224,
    game_time_seconds: 10,
    supply: 12,
    item_name: "SCV",
    category: "worker",
    action: "created",
  },
  {
    player_id: 1,
    game_loop: 448,
    game_time_seconds: 20,
    supply: 13,
    item_name: "Barracks",
    category: "structure",
    action: "started",
  },
];

describe("BuildOrders", () => {
  it("reveals entries as the replay reaches each event", () => {
    const { rerender } = render(
      <BuildOrders entries={entries} players={players} currentTime={0} />,
    );

    expect(screen.queryByText("SCV")).not.toBeInTheDocument();
    expect(screen.queryByText("Barracks")).not.toBeInTheDocument();

    rerender(<BuildOrders entries={entries} players={players} currentTime={10} />);

    expect(screen.getByText("SCV")).toBeInTheDocument();
    expect(screen.queryByText("Barracks")).not.toBeInTheDocument();

    rerender(<BuildOrders entries={entries} players={players} currentTime={20} />);

    expect(screen.getByText("SCV")).toBeInTheDocument();
    expect(screen.getByText("Barracks")).toBeInTheDocument();
  });
});
