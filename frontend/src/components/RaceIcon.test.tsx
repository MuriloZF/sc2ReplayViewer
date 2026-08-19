import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { RaceIcon } from "./RaceIcon";

describe("RaceIcon", () => {
  it.each(["Terran", "Zerg", "Protoss"])("renders an accessible %s emblem", (race) => {
    render(<RaceIcon race={race} />);

    const icon = screen.getByRole("img", { name: `${race} icon` });
    expect(icon).toBeInTheDocument();
    expect(icon).toHaveAttribute("src", expect.stringContaining(`${race.toLowerCase()}.png`));
  });

  it("keeps an accessible fallback for an unknown race", () => {
    render(<RaceIcon race="Random" />);

    expect(screen.getByLabelText("Random icon")).toHaveTextContent("?");
  });
});
