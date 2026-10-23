import { act, cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { getWinProbability } from "../api";
import type { Player, WinProbabilityResponse } from "../types";
import { WinProbability } from "./WinProbability";

vi.mock("../api", () => ({ getWinProbability: vi.fn() }));

const players: Player[] = [
  { player_id: 7, name: "Beta", race: "Zerg", result: "loss", win_probability: null },
  { player_id: 3, name: "Alpha", race: "Terran", result: "win", win_probability: null },
];

const predictions: WinProbabilityResponse = {
  replay_id: "one",
  model_name: "XGBClassifier",
  samples: [
    {
      game_loop: 112,
      game_time_seconds: 5,
      players: [
        { player_id: 3, win_probability: 0.505 },
        { player_id: 7, win_probability: 0.495 },
      ],
    },
    {
      game_loop: 224,
      game_time_seconds: 10,
      players: [
        { player_id: 3, win_probability: 1 },
        { player_id: 7, win_probability: 0 },
      ],
    },
  ],
};

describe("WinProbability", () => {
  afterEach(cleanup);

  beforeEach(() => {
    vi.mocked(getWinProbability).mockReset();
    vi.mocked(getWinProbability).mockResolvedValue(predictions);
  });

  it("maps predictions by player ID and follows the timeline without fetching again", async () => {
    const { rerender, container } = render(
      <WinProbability replayId="one" players={players} gameLoop={112} />,
    );
    expect(screen.getByRole("status")).toHaveTextContent("Calculating win probabilities");
    await screen.findByText("XGBClassifier");
    const beta = screen.getByText("Beta").parentElement!;
    const alpha = screen.getByText("Alpha").parentElement!;
    expect(within(beta).getByText("50%")).toBeInTheDocument();
    expect(within(alpha).getByText("50%")).toBeInTheDocument();

    rerender(<WinProbability replayId="one" players={players} gameLoop={224} />);
    expect(within(beta).getByText("0%")).toBeInTheDocument();
    expect(within(alpha).getByText("100%")).toBeInTheDocument();
    expect(container.querySelector(".probability-segment.player-1")).toHaveStyle({ height: "0%" });
    expect(getWinProbability).toHaveBeenCalledTimes(1);

    rerender(<WinProbability replayId="one" players={players} gameLoop={112} />);
    expect(within(beta).getByText("50%")).toBeInTheDocument();
  });

  it("shows the missing economy state for the opening without borrowing a future prediction", async () => {
    render(<WinProbability replayId="one" players={players} gameLoop={0} />);
    expect(await screen.findByText("Waiting for data")).toBeInTheDocument();
    expect(screen.queryByText("Beta")).not.toBeInTheDocument();
  });

  it("explains model errors inside the probability panel", async () => {
    vi.mocked(getWinProbability).mockRejectedValue(new Error("Win probability model is unavailable."));
    render(<WinProbability replayId="one" players={players} gameLoop={112} />);
    expect(await screen.findByText("Unavailable")).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("Win probability model is unavailable.");
  });

  it("ignores a late response after switching replays", async () => {
    let resolveFirst!: (value: WinProbabilityResponse) => void;
    vi.mocked(getWinProbability).mockReturnValueOnce(
      new Promise((resolve) => { resolveFirst = resolve; }),
    );
    vi.mocked(getWinProbability).mockResolvedValueOnce({
      ...predictions,
      replay_id: "two",
      model_name: "Second model",
    });
    const { rerender } = render(<WinProbability replayId="one" players={players} gameLoop={112} />);
    rerender(<WinProbability replayId="two" players={players} gameLoop={112} />);
    await screen.findByText("Second model");
    await act(async () => resolveFirst(predictions));
    expect(screen.getByText("Second model")).toBeInTheDocument();
    expect(screen.queryByText("XGBClassifier")).not.toBeInTheDocument();
  });
});
