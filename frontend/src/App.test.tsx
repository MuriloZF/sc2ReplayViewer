import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import App from "./App";

describe("App", () => {
  it("introduces the replay viewer", () => {
    render(<App />);

    expect(screen.getByRole("heading", { name: "SC2 Replay Viewer" })).toBeInTheDocument();
  });
});
