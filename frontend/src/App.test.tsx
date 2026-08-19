import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import App from "./App";

describe("App", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ items: [] }),
      }),
    );
  });

  it("offers replay upload and shows the current session", async () => {
    render(<App />);

    expect(
      screen.getByRole("heading", { name: "Analyze a StarCraft II replay." }),
    ).toBeInTheDocument();
    expect(screen.getByLabelText(/choose a .sc2replay file/i)).toBeInTheDocument();
    expect(await screen.findByText("Replays you analyze will appear here until the API restarts.")).toBeInTheDocument();
  });
});
